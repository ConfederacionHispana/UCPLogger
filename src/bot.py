import aiohttp
import asyncio
import logging.config
import signal
import sys
import traceback
from collections import defaultdict

import requests

from src.argparser import command_line_args
from src.config import settings
from src.database import db_cursor
from src.exceptions import *
from src.misc import get_paths, get_domain
from src.msgqueue import messagequeue
from src.queue_handler import DBHandler
from src.wiki import Wiki, process_cats, process_mwmsgs, essential_info, essential_feeds
from src.discord import DiscordMessage, formatter_exception_logger, msg_sender_exception_logger

logging.config.dictConfig(settings["logging"])
logger = logging.getLogger("rcgcdb.bot")
logger.debug("Current settings: {settings}".format(settings=settings))
logger.info("RcGcDb v{} is starting up.".format("1.0"))

if command_line_args.debug:
	logger.info("Debug mode is active!")

# Log Fail states with structure wiki_url: number of fail states
all_wikis: dict = {}
mw_msgs: dict = {}  # will have the type of id: tuple

# First populate the all_wikis list with every wiki
# Reasons for this: 1. we require amount of wikis to calculate the cooldown between requests
# 2. Easier to code

for wiki in db_cursor.execute('SELECT DISTINCT wiki FROM rcgcdw'):
	all_wikis[wiki] = Wiki()


# Start queueing logic


def calculate_delay_for_group(group_length: int) -> float:
	"""Calculate the delay between fetching each wiki to avoid rate limits"""
	min_delay = 60 / settings["max_requests_per_minute"]
	if (group_length * min_delay) < settings["minimal_cooldown_per_wiki_in_sec"]:
		return settings["minimal_cooldown_per_wiki_in_sec"] / group_length
	else:
		return min_delay


def generate_targets(wiki_url: str) -> defaultdict:
	"""To minimize the amount of requests, we generate a list of language/display mode combinations to create messages for
	this way we can send the same message to multiple webhooks which have the same wiki and settings without doing another
	request to the wiki just to duplicate the message.
	"""
	combinations = defaultdict(list)
	for webhook in db_cursor.execute('SELECT webhook, lang, display FROM rcgcdw WHERE wiki = ?', (wiki_url,)):
		combination = (webhook["lang"], webhook["display"])
		combinations[combination].append(webhook["webhook"])
	return combinations


async def generate_domain_groups():  # oh boy, I cannot wait to learn about async generators
	combinations = defaultdict(list)
	fetch_all = db_cursor.execute('SELECT webhook, wiki, lang, display, wikiid, rcid FROM rcgcdw GROUP BY wiki')
	for db_wiki in fetch_all.fetchall():
		combinations[get_domain(db_wiki["wiki"])].append(db_wiki)
	for item in combinations.values():
		yield item


async def scan_group(group: list):
	calc_delay = calculate_delay_for_group(len(group))
	for db_wiki in group:
		logger.debug("Wiki {}".format(db_wiki["wiki"]))
		if db_wiki["wiki"] not in all_wikis:
			logger.info("Registering new wiki locally: {}".format(db_wiki["wiki"]))
			all_wikis[db_wiki["wiki"]] = Wiki()
		local_wiki = all_wikis[db_wiki["wiki"]]  # set a reference to a wiki object from memory
		if db_wiki["rcid"] != -1:
			extended = False
			if local_wiki.mw_messages is None:
				extended = True
			async with aiohttp.ClientSession(headers=settings["header"],
			                                 timeout=aiohttp.ClientTimeout(3.0)) as session:
				try:
					wiki_response = await local_wiki.fetch_wiki(extended, db_wiki["wiki"], session)
					await local_wiki.check_status(db_wiki["wiki"], wiki_response.status)
				except (WikiServerError, WikiError):
					logger.error("Exeption when fetching the wiki")
					continue  # ignore this wiki if it throws errors
				try:
					recent_changes_resp = await wiki_response.json()
					if "error" in recent_changes_resp or "errors" in recent_changes_resp:
						error = recent_changes_resp.get("error", recent_changes_resp["errors"])
						if error["code"] == "readapidenied":
							await local_wiki.fail_add(db_wiki["wiki"], 410)
							continue
						raise WikiError
					recent_changes = recent_changes_resp['query']['recentchanges']
					recent_changes.reverse()
				except aiohttp.ContentTypeError:
					logger.exception("Wiki seems to be resulting in non-json content.")
					await local_wiki.fail_add(db_wiki["wiki"], 410)
					continue
				except:
					logger.exception("On loading json of response.")
					continue
			if extended:
				await process_mwmsgs(recent_changes_resp, local_wiki, mw_msgs)
			if db_wiki["rcid"] is None:  # new wiki, just get the last rc to not spam the channel
				if len(recent_changes) > 0:
					DBHandler.add(db_wiki["wiki"], recent_changes[-1]["rcid"])
				else:
					DBHandler.add(db_wiki["wiki"], 0)
				DBHandler.update_db()
				continue
			categorize_events = {}
			targets = generate_targets(db_wiki["wiki"])
			paths = get_paths(db_wiki["wiki"], recent_changes_resp)
			for change in recent_changes:
				await process_cats(change, local_wiki, mw_msgs, categorize_events)
			for change in recent_changes:  # Yeah, second loop since the categories require to be all loaded up
				if change["rcid"] > db_wiki["rcid"]:
					for target in targets.items():
						try:
							await essential_info(change, categorize_events, local_wiki, db_wiki,
							                     target, paths, recent_changes_resp)
						except:
							if command_line_args.debug:
								raise  # reraise the issue
							else:
								logger.exception("Exception on RC formatter")
								await formatter_exception_logger(db_wiki["wiki"], change, traceback.format_exc())
			if recent_changes:
				DBHandler.add(db_wiki["wiki"], change["rcid"])
		await asyncio.sleep(delay=calc_delay)


async def wiki_scanner():
	"""Wiki scanner is spawned as a task which purpose is to continuously run over wikis in the DB, fetching recent changes
	to add messages based on the changes to message queue later handled by message_sender coroutine."""
	try:
		while True:
			async for group in generate_domain_groups():
				asyncio.create_task(scan_group(group))

			fetch_all = db_cursor.execute(
				'SELECT webhook, wiki, lang, display, wikiid, rcid, postid FROM rcgcdw GROUP BY wiki')
			for db_wiki in fetch_all.fetchall():

				if db_wiki["wikiid"] is not None:
					header = settings["header"]
					header["Accept"] = "application/hal+json"
					async with aiohttp.ClientSession(headers=header,
					                                 timeout=aiohttp.ClientTimeout(3.0)) as session:
						try:
							feeds_response = await local_wiki.fetch_feeds(db_wiki["wikiid"], session)
						except (WikiServerError, WikiError):
							logger.error("Exeption when fetching the wiki")
							continue  # ignore this wiki if it throws errors
						try:
							discussion_feed_resp = await feeds_response.json(encoding="UTF-8")
							if "title" in discussion_feed_resp:
								error = discussion_feed_resp["error"]
								if error == "site doesn't exists":
									db_cursor.execute("UPDATE rcgcdw SET wikiid = ? WHERE wiki = ?",
									                  (None, db_wiki["wiki"],))
									DBHandler.update_db()
									continue
								raise WikiError
							discussion_feed = discussion_feed_resp["_embedded"]["doc:posts"]
							discussion_feed.reverse()
						except aiohttp.ContentTypeError:
							logger.exception("Wiki seems to be resulting in non-json content.")
							continue
						except:
							logger.exception("On loading json of response.")
							continue
					if db_wiki["postid"] is None:  # new wiki, just get the last post to not spam the channel
						if len(discussion_feed) > 0:
							DBHandler.add(db_wiki["wiki"], discussion_feed[-1]["id"], True)
						else:
							DBHandler.add(db_wiki["wiki"], "0", True)
						DBHandler.update_db()
						continue
					targets = generate_targets(db_wiki["wiki"])
					for post in discussion_feed:
						if post["id"] > db_wiki["postid"]:
							for target in targets.items():
								try:
									await essential_feeds(post, db_wiki, target)
								except:
									if command_line_args.debug:
										raise  # reraise the issue
									else:
										logger.exception("Exception on Feeds formatter")
										await formatter_exception_logger(db_wiki["wiki"], post, traceback.format_exc())
					if discussion_feed:
						DBHandler.add(db_wiki["wiki"], post["id"], True)
				await asyncio.sleep(delay=calc_delay)
			DBHandler.update_db()
	except asyncio.CancelledError:
		raise


async def message_sender():
	"""message_sender is a coroutine responsible for handling Discord messages and their sending to Discord"""
	try:
		while True:
			await messagequeue.resend_msgs()
	except:
		if command_line_args.debug:
			logger.exception("Exception on DC message sender")
			raise  # reraise the issue
		else:
			logger.exception("Exception on DC message sender")
			await msg_sender_exception_logger(traceback.format_exc())


def shutdown(loop, signal=None):
	DBHandler.update_db()
	if len(messagequeue) > 0:
		logger.warning("Some messages are still queued!")
	loop.stop()
	logger.info("Script has shut down due to signal {}.".format(signal))
	for task in asyncio.all_tasks(loop):
		logger.debug("Killing task {}".format(task.get_name()))
		task.cancel()
	sys.exit(0)


def global_exception_handler(loop, context):
	"""Global exception handler for asyncio, lets us know when something crashes"""
	msg = context.get("exception", context["message"])
	logger.error("Global exception handler: {}".format(msg))
	if command_line_args.debug is False:
		requests.post("https://discord.com/api/webhooks/"+settings["monitoring_webhook"], data=repr(DiscordMessage("compact", "monitoring", [settings["monitoring_webhook"]], wiki=None, content="[RcGcDb] Global exception handler: {}".format(msg))), headers={'Content-Type': 'application/json'})
	else:
		shutdown(loop)


async def main_loop():
	loop = asyncio.get_event_loop()
	try:
		signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
		for s in signals:
			loop.add_signal_handler(
				s, lambda s=s: shutdown(loop, signal=s))
	except AttributeError:
		logger.info("Running on Windows, some things may not work as they should.")
		signals = (signal.SIGBREAK, signal.SIGTERM, signal.SIGINT)
	loop.set_exception_handler(global_exception_handler)
	try:
		task1 = asyncio.create_task(wiki_scanner())
		task2 = asyncio.create_task(message_sender())
		await task1
		await task2
	except KeyboardInterrupt:
		shutdown(loop)


asyncio.run(main_loop(), debug=command_line_args.debug)
