import datetime, logging
import json
from urllib.parse import quote_plus

from src.config import settings
from src.misc import link_formatter, create_article_path, escape_formatting
from src.discord import DiscordMessage
from src.msgqueue import send_to_discord
from src.i18n import langs


logger = logging.getLogger("rcgcdw.discussion_formatters")

async def feeds_compact_formatter(post_type, post, message_target, wiki):
	"""Compact formatter for Fandom discussions."""
	_ = langs[message_target[0][0]]["discussion_formatters"].gettext
	message = None
	if post_type == "FORUM":
		author = post["createdBy"]["name"]
		author_url = "<{url}f/u/{creatorId}>".format(url=wiki, creatorId=post["creatorId"])
	elif post["creatorIp"]:
		author = post["creatorIp"][1:]
		author_url = "<{url}wiki/Special:Contributions{creatorIp}>".format(url=wiki, creatorIp=post["creatorIp"])
	else:
		author = post["createdBy"]["name"]
		author_url = link_formatter(create_article_path("User:{user}".format(user=author), wiki + "wiki/$1"))
	if post_type == "FORUM":
		if not post["isReply"]:
			thread_funnel = post.get("funnel")
			msg_text = _("[{author}]({author_url}) created [{title}](<{url}f/p/{threadId}>) in {forumName}")
			if thread_funnel == "POLL":
				msg_text = _("[{author}]({author_url}) created a poll [{title}](<{url}f/p/{threadId}>) in {forumName}")
			elif thread_funnel == "QUIZ":
				msg_text = _("[{author}]({author_url}) created a quiz [{title}](<{url}f/p/{threadId}>) in {forumName}")
			elif thread_funnel != "TEXT":
				logger.warning("No entry for {event} with params: {params}".format(event=thread_funnel, params=post))
			message = msg_text.format(author=author, author_url=author_url, title=post["title"], url=wiki, threadId=post["threadId"], forumName=post["forumName"])
		else:
			message = _("[{author}]({author_url}) created a [reply](<{url}f/p/{threadId}/r/{postId}>) to [{title}](<{url}f/p/{threadId}>) in {forumName}").format(author=author, author_url=author_url, url=wiki, threadId=post["threadId"], postId=post["id"], title=post["_embedded"]["thread"][0]["title"], forumName=post["forumName"])
	elif post_type == "WALL":
		user_wall = _("unknown")  # Fail safe
		if post["forumName"].endswith(' Message Wall'):
			user_wall = post["forumName"][:-13]
		if not post["isReply"]:
			message = _("[{author}]({author_url}) created [{title}](<{url}wiki/Message_Wall:{user_wall}?threadId={threadId}>) on [{user}'s Message Wall](<{url}wiki/Message_Wall:{user_wall}>)").format(author=author, author_url=author_url, title=post["title"], url=wiki, user=user_wall, user_wall=quote_plus(user_wall.replace(" ", "_")), threadId=post["threadId"])
		else:
			message = _("[{author}]({author_url}) created a [reply](<{url}wiki/Message_Wall:{user_wall}?threadId={threadId}#{replyId}>) to [{title}](<{url}wiki/Message_Wall:{user_wall}?threadId={threadId}) on [{user}'s Message Wall](<{url}wiki/Message_Wall:{user_wall}>)").format(author=author, author_url=author_url, url=wiki, title=post["_embedded"]["thread"][0]["title"], user=user_wall, user_wall=quote_plus(user_wall.replace(" ", "_")), threadId=post["threadId"], replyId=post["id"])
	elif post_type == "ARTICLE_COMMENT":
		article_page = _("unknown")  # No page known
		if not post["isReply"]:
			message = _("[{author}]({author_url}) created a [comment](<{url}wiki/{article}?commentId={commentId}>) on [{article}](<{url}wiki/{article}>)").format(author=author, author_url=author_url, url=wiki, article=article_page, commentId=post["threadId"])
		else:
			message = _("[{author}]({author_url}) created a [reply](<{url}wiki/{article}?threadId={threadId}) to a [comment](<{url}wiki/{article}?commentId={commentId}&replyId={replyId}>) on [{article}](<{url}wiki/{article}>)").format(author=author, author_url=author_url, url=wiki, article=article_page, commentId=post["threadId"], replyId=post["id"])
	else:
		logger.warning("No entry for {event} with params: {params}".format(event=post_type, params=post))
		if not settings["support"]:
			return
		else:
			content = _("Unknown event `{event}` by [{author}]({author_url}), report it on the [support server](<{support}>).").format(event=post_type, author=author, author_url=author_url, support=settings["support"])
	await send_to_discord(DiscordMessage("compact", "discussion", message_target[1], content=message, wiki=wiki))


async def feeds_embed_formatter(post_type, post, message_target, wiki):
	"""Embed formatter for Fandom discussions."""
	_ = langs[message_target[0][0]]["discussion_formatters"].gettext
	embed = DiscordMessage("embed", "discussion", message_target[1], wiki=wiki)
	if post_type == "FORUM":
		embed.set_author(post["createdBy"]["name"], "{url}f/u/{creatorId}".format(url=wiki, creatorId=post["creatorId"]), icon_url=post["createdBy"]["avatarUrl"])
	elif post["creatorIp"]:
		embed.set_author(post["creatorIp"][1:], "{url}wiki/Special:Contributions{creatorIp}".format(url=wiki, creatorIp=post["creatorIp"]))
	else:
		embed.set_author(post["createdBy"]["name"], "{url}wiki/User:{creator}".format(url=wiki, creator=post["createdBy"]["name"]), icon_url=post["createdBy"]["avatarUrl"])
	if message_target[0][1] == 3:
		if post.get("jsonModel") is not None:
			npost = DiscussionsFromHellParser(post, wiki)
			embed["description"] = npost.parse()
			if npost.image_last:
				embed["image"]["url"] = npost.image_last
				embed["description"] = embed["description"].replace(npost.image_last, "")
		else:  # Fallback when model is not available
			embed["description"] = post.get("rawContent", "")
	embed["footer"]["text"] = post["forumName"]
	embed["timestamp"] = datetime.datetime.fromtimestamp(post["creationDate"]["epochSecond"], tz=datetime.timezone.utc).isoformat()
	if post_type == "FORUM":
		if not post["isReply"]:
			embed["url"] = "{url}f/p/{threadId}".format(url=wiki, threadId=post["threadId"])
			embed["title"] = _("Created \"{title}\"").format(title=post["title"])
			thread_funnel = post.get("funnel")
			if thread_funnel == "POLL":
				embed.event_type = "discussion/forum/poll"
				embed["title"] = _("Created a poll \"{title}\"").format(title=post["title"])
				if message_target[0][1] > 1:
					poll = post["poll"]
					image_type = False
					if poll["answers"][0]["image"] is not None:
						image_type = True
					for num, option in enumerate(poll["answers"]):
						embed.add_field(option["text"] if image_type is True else _("Option {}").format(num+1),
										option["text"] if image_type is False else _("__[View image]({image_url})__").format(image_url=option["image"]["url"]),
										inline=True)
			elif thread_funnel == "QUIZ":
				embed.event_type = "discussion/forum/quiz"
				embed["title"] = _("Created a quiz \"{title}\"").format(title=post["title"])
				if message_target[0][1] > 1:
					quiz = post["_embedded"]["quizzes"][0]
					embed["description"] = quiz["title"]
					if quiz["image"] is not None:
						embed["image"]["url"] = quiz["image"]
			elif thread_funnel == "TEXT":
				embed.event_type = "discussion/forum/post"
			else:
				logger.warning("No entry for {event} with params: {params}".format(event=thread_funnel, params=post))
			if message_target[0][1] > 1 and post["_embedded"]["thread"][0]["tags"]:
				tag_displayname = []
				for tag in post["_embedded"]["thread"][0]["tags"]:
					tag_displayname.append("[{title}]({url})".format(title=tag["articleTitle"], url=create_article_path(tag["articleTitle"], wiki + "wiki/$1")))
				if len(", ".join(tag_displayname)) > 1000:
					embed.add_field(_("Tags"), _("{} tags").format(len(post["_embedded"]["thread"][0]["tags"])))
				else:
					embed.add_field(_("Tags"), ", ".join(tag_displayname))
		else:
			embed.event_type = "discussion/forum/reply"
			embed["title"] = _("Replied to \"{title}\"").format(title=post["_embedded"]["thread"][0]["title"])
			embed["url"] = "{url}f/p/{threadId}/r/{postId}".format(url=wiki, threadId=post["threadId"], postId=post["id"])
	elif post_type == "WALL":
		user_wall = _("unknown")  # Fail safe
		if post["forumName"].endswith(' Message Wall'):
			user_wall = post["forumName"][:-13]
		if not post["isReply"]:
			embed.event_type = "discussion/wall/post"
			embed["url"] = "{url}wiki/Message_Wall:{user_wall}?threadId={threadId}".format(url=wiki, user_wall=quote_plus(user_wall.replace(" ", "_")), threadId=post["threadId"])
			embed["title"] = _("Created \"{title}\" on {user}'s Message Wall").format(title=post["title"], user=user_wall)
		else:
			embed.event_type = "discussion/wall/reply"
			embed["url"] = "{url}wiki/Message_Wall:{user_wall}?threadId={threadId}#{replyId}".format(url=wiki, user_wall=quote_plus(user_wall.replace(" ", "_")), threadId=post["threadId"], replyId=post["id"])
			embed["title"] = _("Replied to \"{title}\" on {user}'s Message Wall").format(title=post["_embedded"]["thread"][0]["title"], user=user_wall)
	elif post_type == "ARTICLE_COMMENT":
		article_page = _("unknown")  # No page known
		if not post["isReply"]:
			embed.event_type = "discussion/comment/post"
			# embed["url"] = "{url}wiki/{article}?commentId={commentId}".format(url=wiki, article=quote_plus(article_page.replace(" ", "_")), commentId=post["threadId"])
			embed["title"] = _("Commented on {article}").format(article=article_page)
		else:
			embed.event_type = "discussion/comment/reply"
			# embed["url"] = "{url}wiki/{article}?commentId={commentId}&replyId={replyId}".format(url=wiki, article=quote_plus(article_page.replace(" ", "_")), commentId=post["threadId"], replyId=post["id"])
			embed["title"] = _("Replied to a comment on {article}").format(article=article_page)
		embed["footer"]["text"] = article_page
	else:
		logger.warning("No entry for {event} with params: {params}".format(event=post_type, params=post))
		embed["title"] = _("Unknown event `{event}`").format(event=post_type)
		embed["color"] = 0
		if settings["support"]:
			change_params = "[```json\n{params}\n```]({support})".format(params=json.dumps(post, indent=2), support=settings["support"])
			if len(change_params) > 1000:
				embed.add_field(_("Report this on the support server"), settings["support"])
			else:
				embed.add_field(_("Report this on the support server"), change_params)
	embed.finish_embed()
	await send_to_discord(embed)


class DiscussionsFromHellParser:
	"""This class converts fairly convoluted Fandom jsonModal of a discussion post into Markdown formatted usable thing. Takes string, returns string.
		Kudos to MarkusRost for allowing me to implement this formatter based on his code in Wiki-Bot."""
	def __init__(self, post, wiki):
		self.post = post
		self.wiki = wiki
		self.jsonModal = json.loads(post.get("jsonModel", "{}"))
		self.markdown_text = ""
		self.item_num = 1
		self.image_last = None

	def parse(self) -> str:
		"""Main parsing logic"""
		self.parse_content(self.jsonModal["content"])
		if len(self.markdown_text) > 2000:
			self.markdown_text = self.markdown_text[0:2000] + "…"
		return self.markdown_text

	def parse_content(self, content, ctype=None):
		self.image_last = None
		for item in content:
			if ctype == "bulletList":
				self.markdown_text += "\t• "
			if ctype == "orderedList":
				self.markdown_text += "\t{num}. ".format(num=self.item_num)
				self.item_num += 1
			if item["type"] == "text":
				if "marks" in item:
					prefix, suffix = self.convert_marks(item["marks"])
					self.markdown_text = "{old}{pre}{text}{suf}".format(old=self.markdown_text, pre=prefix, text=escape_formatting(item["text"]), suf=suffix)
				else:
					if ctype == "code_block":
						self.markdown_text += item["text"]  # ignore formatting on preformatted text which cannot have additional formatting anyways
					else:
						self.markdown_text += escape_formatting(item["text"])
			elif item["type"] == "paragraph":
				if "content" in item:
					self.parse_content(item["content"], item["type"])
				self.markdown_text += "\n"
			elif item["type"] == "openGraph":
				if not item["attrs"].get("wasAddedWithInlineLink", False):
					self.markdown_text = "{old}{link}\n".format(old=self.markdown_text, link=item["attrs"]["url"])
			elif item["type"] == "image":
				try:
					logger.debug(item["attrs"]["id"])
					if item["attrs"]["id"] is not None:
						self.markdown_text = "{old}{img_url}\n".format(old=self.markdown_text, img_url=self.post["_embedded"]["contentImages"][int(item["attrs"]["id"])]["url"])
					self.image_last = self.post["_embedded"]["contentImages"][int(item["attrs"]["id"])]["url"]
				except (IndexError, ValueError, TypeError):
					logger.warning("Image {} not found.".format(item["attrs"]["id"]))
				logger.debug(self.markdown_text)
			elif item["type"] == "code_block":
				self.markdown_text += "```\n"
				if "content" in item:
					self.parse_content(item["content"], item["type"])
				self.markdown_text += "\n```\n"
			elif item["type"] == "bulletList":
				if "content" in item:
					self.parse_content(item["content"], item["type"])
			elif item["type"] == "orderedList":
				self.item_num = 1
				if "content" in item:
					self.parse_content(item["content"], item["type"])
			elif item["type"] == "listItem":
				self.parse_content(item["content"], item["type"])

	def convert_marks(self, marks):
		prefix = ""
		suffix = ""
		for mark in marks:
			if mark["type"] == "mention":
				prefix += "["
				suffix = "]({wiki}f/u/{userid}){suffix}".format(wiki=self.wiki, userid=mark["attrs"]["userId"], suffix=suffix)
			elif mark["type"] == "strong":
				prefix += "**"
				suffix = "**{suffix}".format(suffix=suffix)
			elif mark["type"] == "link":
				prefix += "["
				suffix = "]({link}){suffix}".format(link=mark["attrs"]["href"], suffix=suffix)
			elif mark["type"] == "em":
				prefix += "_"
				suffix = "_" + suffix
		return prefix, suffix