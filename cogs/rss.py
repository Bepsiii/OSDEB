# cogs/rss.py
"""
Cog for fetching RSS feed updates, summarizing them with Gemini AI,
and posting hourly news roundups to a specified Discord channel.
"""
import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
import logging
import aiohttp
import feedparser
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import hashlib
import calendar

# Assuming your config.py and gemini_service.py are accessible
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
# GeminiService will be accessed via self.bot.gemini_service

# --- Logger Setup ---
logger = logging.getLogger(__name__)

class ArticleData:
    """Simple class to hold extracted article data for summarization."""
    def __init__(self, title: str, link: Optional[str], summary: Optional[str], published_dt: Optional[datetime], feed_title: str):
        self.title = title
        self.link = link
        self.summary = summary
        self.published_dt = published_dt
        self.feed_title = feed_title

    def __str__(self): # For easy inclusion in prompts
        date_str = self.published_dt.strftime('%Y-%m-%d %H:%M UTC') if self.published_dt else "N/A"
        return (
            f"Title: {self.title}\n"
            f"Feed: {self.feed_title}\n"
            f"Link: {self.link or 'N/A'}\n"
            f"Published: {date_str}\n"
            f"Summary: {self.summary or 'N/A'}\n"
        )

class RSSFeed:
    """Represents a subscribed RSS feed."""
    def __init__(self, url: str, original_channel_id: int, guild_id: int,
                 last_seen_entry_id: Optional[str] = None,
                 feed_title: Optional[str] = None,
                 added_by: Optional[int] = None):
        self.url = url
        self.original_channel_id = original_channel_id # Channel where 'add' command was used, for context/errors
        self.guild_id = guild_id
        self.last_seen_entry_id = last_seen_entry_id
        self.feed_title = feed_title
        self.added_by = added_by
        self.last_checked: Optional[datetime] = None
        self.error_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "original_channel_id": self.original_channel_id,
            "guild_id": self.guild_id,
            "last_seen_entry_id": self.last_seen_entry_id,
            "feed_title": self.feed_title,
            "added_by": self.added_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RSSFeed':
        return cls(
            url=data["url"],
            original_channel_id=data.get("original_channel_id", data.get("channel_id")), # Backwards compatibility
            guild_id=data.get("guild_id"),
            last_seen_entry_id=data.get("last_seen_entry_id"),
            feed_title=data.get("feed_title"),
            added_by=data.get("added_by")
        )

class RSSCog(commands.Cog, name="RSSSummarizer"): # Renamed for clarity
    """Monitors RSS feeds and posts AI-generated hourly summaries."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.feeds_file_path: str = getattr(config, 'RSS_FEEDS_FILE_PATH', 'data/rss_feeds.json')
        self.subscribed_feeds: List[RSSFeed] = []
        self.collected_articles_for_summary: List[ArticleData] = [] # Stores ArticleData objects
        self.lock = asyncio.Lock()
        self.user_agent = getattr(config, 'RSS_USER_AGENT', f'DiscordBot/{discord.__version__} (RSSCog/2.0)')
        self.request_timeout = getattr(config, 'RSS_REQUEST_TIMEOUT_SECONDS', 15)

        data_dir = os.path.dirname(self.feeds_file_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)

        self.bot.loop.create_task(self._load_feeds())
        self.check_rss_feeds_loop.start()
        if getattr(config, 'RSS_HOURLY_SUMMARY_ENABLED', False):
            self.post_hourly_summary_loop.start()
        else:
            logger.info("RSS Hourly Summary feature is disabled in config.")

    async def _load_feeds(self):
        # (Same as previous version - loads from rss_feeds.json)
        async with self.lock:
            try:
                if os.path.exists(self.feeds_file_path):
                    with open(self.feeds_file_path, 'r', encoding='utf-8') as f:
                        feeds_data = json.load(f)
                        self.subscribed_feeds = [RSSFeed.from_dict(data) for data in feeds_data]
                    logger.info(f"RSS: Loaded {len(self.subscribed_feeds)} feed subscriptions.")
                else:
                    with open(self.feeds_file_path, 'w', encoding='utf-8') as f: json.dump([], f)
                    logger.info(f"RSS: Feeds file not found, created empty: {self.feeds_file_path}")
            except Exception as e:
                logger.error(f"RSS: Error loading feeds: {e}", exc_info=True)

    async def _save_feeds(self):
        # (Same as previous version - saves to rss_feeds.json)
        async with self.lock:
            try:
                with open(self.feeds_file_path, 'w', encoding='utf-8') as f:
                    json.dump([feed.to_dict() for feed in self.subscribed_feeds], f, indent=4)
                logger.debug(f"RSS: Saved {len(self.subscribed_feeds)} feed subscriptions.")
            except Exception as e:
                logger.error(f"RSS: Error saving feeds: {e}", exc_info=True)


    def get_entry_id(self, entry: feedparser.FeedParserDict) -> str:
        # (Same as previous version)
        if hasattr(entry, 'id') and entry.id: return entry.id
        if hasattr(entry, 'link') and entry.link: return entry.link
        published_str = str(entry.get('published_parsed') or entry.get('updated_parsed') or '')
        content_to_hash = (entry.get('title', '') + entry.get('summary', '') + published_str).encode('utf-8')
        return hashlib.md5(content_to_hash).hexdigest()

    def extract_article_data(self, entry: feedparser.FeedParserDict, feed_title: str) -> ArticleData:
        """Extracts relevant data from a feed entry into an ArticleData object."""
        title = entry.get('title', 'No Title')
        link = entry.get('link')
        summary = "No summary available."
        if hasattr(entry, 'summary'): summary = entry.summary
        elif hasattr(entry, 'description'): summary = entry.description
        if summary: # Basic HTML cleaning
            summary = summary.replace('<br />', '\n').replace('<br>', '\n')
            import re
            summary = re.sub('<[^<]+?>', '', summary).strip()
            max_desc_len = getattr(config, 'RSS_MAX_DESCRIPTION_LENGTH', 300) # Use for individual summary if needed
            if len(summary) > max_desc_len: summary = summary[:max_desc_len-3] + "..."
        
        published_dt: Optional[datetime] = None
        time_struct = entry.get('published_parsed') or entry.get('updated_parsed')
        if time_struct:
            try:
                utc_timestamp = calendar.timegm(time_struct)
                published_dt = datetime.fromtimestamp(utc_timestamp, timezone.utc)
            except Exception as e:
                logger.warning(f"RSS: Could not parse date for entry '{title}': {e}")
        return ArticleData(title, link, summary, published_dt, feed_title)


    @tasks.loop(seconds=getattr(config, 'RSS_CHECK_INTERVAL_SECONDS', 900))
    async def check_rss_feeds_loop(self):
        """Periodically checks subscribed RSS feeds for new articles to collect for summary."""
        logger.info("RSS: Starting periodic feed check for article collection...")
        if not self.subscribed_feeds:
            logger.info("RSS: No feeds subscribed. Skipping collection.")
            return

        new_articles_collected_this_run = 0
        async with aiohttp.ClientSession(headers={'User-Agent': self.user_agent}) as session:
            for feed_subscription in list(self.subscribed_feeds):
                try:
                    logger.debug(f"RSS: Checking feed: {feed_subscription.url} (Guild: {feed_subscription.guild_id})")
                    async with session.get(feed_subscription.url, timeout=self.request_timeout) as response:
                        if response.status != 200:
                            logger.warning(f"RSS: Fetch failed for {feed_subscription.url}. Status: {response.status}")
                            feed_subscription.error_count += 1; continue
                        feed_subscription.error_count = 0
                        content = await response.text()
                    
                    parsed_feed = await self.bot.loop.run_in_executor(None, feedparser.parse, content)
                    if parsed_feed.bozo:
                        logger.warning(f"RSS: Feed {feed_subscription.url} not well-formed: {parsed_feed.bozo_exception}")

                    current_feed_title = feed_subscription.feed_title
                    if not current_feed_title and parsed_feed.feed and parsed_feed.feed.get('title'):
                        feed_subscription.feed_title = parsed_feed.feed.title
                    
                    newly_fetched_entries = []
                    if parsed_feed.entries:
                        for entry in parsed_feed.entries:
                            entry_id = self.get_entry_id(entry)
                            if feed_subscription.last_seen_entry_id and entry_id == feed_subscription.last_seen_entry_id:
                                break
                            newly_fetched_entries.append(entry)
                    
                    # Process oldest of the new entries first for collection
                    entries_to_collect = list(reversed(newly_fetched_entries))

                    if feed_subscription.last_seen_entry_id is None and entries_to_collect:
                        max_first = getattr(config, 'RSS_MAX_ARTICLES_ON_FIRST_FETCH', 1)
                        entries_to_collect = entries_to_collect[-max_first:]
                    
                    if entries_to_collect:
                        logger.info(f"RSS: Found {len(entries_to_collect)} new entries from {feed_subscription.url} to collect.")
                        latest_entry_id_this_feed = None
                        for entry_data in entries_to_collect:
                            article = self.extract_article_data(entry_data, feed_subscription.feed_title or parsed_feed.feed.get('title', feed_subscription.url))
                            # Add guild_id to article data if needed for multi-guild summaries (not currently used like that)
                            # article.guild_id = feed_subscription.guild_id 
                            async with self.lock: # Lock when modifying shared list
                                self.collected_articles_for_summary.append(article)
                            new_articles_collected_this_run += 1
                            latest_entry_id_this_feed = self.get_entry_id(entry_data)
                        
                        if latest_entry_id_this_feed:
                            feed_subscription.last_seen_entry_id = latest_entry_id_this_feed
                        
                        if new_articles_collected_this_run > 0 or current_feed_title != feed_subscription.feed_title:
                            await self._save_feeds() # Save if new articles processed or title changed

                    feed_subscription.last_checked = datetime.now(timezone.utc)
                except Exception as e:
                    logger.error(f"RSS: Error processing feed {feed_subscription.url}: {e}", exc_info=True)
                    feed_subscription.error_count += 1
        
        if new_articles_collected_this_run > 0:
            logger.info(f"RSS: Collection check finished. Collected {new_articles_collected_this_run} new articles for potential summary.")
        else:
            logger.info("RSS: Collection check finished. No new articles collected.")

    @tasks.loop(hours=getattr(config, 'RSS_SUMMARY_INTERVAL_HOURS', 1))
    async def post_hourly_summary_loop(self):
        await self.bot.wait_until_ready() # Ensure bot is ready before first run
        logger.info("RSS: Hourly summary task triggered.")

        if not getattr(config, 'RSS_HOURLY_SUMMARY_ENABLED', False):
            logger.info("RSS: Hourly summary is disabled in config. Skipping.")
            return

        summary_channel_id = getattr(config, 'RSS_SUMMARY_CHANNEL_ID', 0)
        if not summary_channel_id:
            logger.warning("RSS: RSS_SUMMARY_CHANNEL_ID is not set in config. Cannot post summary.")
            return
        
        target_channel = self.bot.get_channel(summary_channel_id)
        if not target_channel or not isinstance(target_channel, discord.TextChannel):
            logger.error(f"RSS: Summary channel ID {summary_channel_id} not found or not a text channel.")
            return

        async with self.lock: # Access collected articles under lock
            if not self.collected_articles_for_summary:
                logger.info("RSS: No articles collected for this summary period.")
                # Optionally send a "no news" message if configured
                # await target_channel.send(getattr(config, 'RSS_NO_NEW_ARTICLES_FOR_SUMMARY_MESSAGE', "No new articles to summarize this hour."))
                return

            min_articles = getattr(config, 'RSS_MIN_ARTICLES_FOR_SUMMARY', 3)
            if len(self.collected_articles_for_summary) < min_articles:
                logger.info(f"RSS: Not enough new articles ({len(self.collected_articles_for_summary)} collected, {min_articles} min) for summary. Holding them for next cycle.")
                return

            articles_to_summarize = self.collected_articles_for_summary[:getattr(config, 'RSS_MAX_ARTICLES_IN_PROMPT_FOR_SUMMARY', 15)]
            
            # Construct prompt for Gemini
            articles_text_for_prompt = "\n\n---\n\n".join([str(art) for art in articles_to_summarize])
            full_prompt = getattr(config, 'RSS_GEMINI_SUMMARY_PROMPT', "Summarize these articles:\n{articles_text}").format(articles_text=articles_text_for_prompt)

            # Ensure Gemini service is available
            if not hasattr(self.bot, 'gemini_service') or not self.bot.gemini_service.model:
                logger.error("RSS: Gemini service not available on bot instance. Cannot generate summary.")
                # Optionally clear articles or they will be re-attempted next hour
                # self.collected_articles_for_summary = [] # Clear to avoid re-processing if Gemini is down long term
                return

            logger.info(f"RSS: Sending {len(articles_to_summarize)} articles to Gemini for summarization.")
            
            summary_response_text = None
            try:
                summary_response_text = await self.bot.gemini_service.generate_content(full_prompt)
            except Exception as e:
                logger.error(f"RSS: Error getting summary from Gemini: {e}", exc_info=True)
                # Decide how to handle: try again next hour with same articles, or clear them?
                # For now, articles remain for next attempt.
                return 

            if summary_response_text:
                logger.info("RSS: Successfully received summary from Gemini.")
                summary_header = getattr(config, 'RSS_SUMMARY_POST_HEADER', "📰 **Hourly News Roundup!**")
                
                # Post summary (handle length)
                full_message = f"{summary_header}\n\n{summary_response_text}"
                max_len = getattr(config, 'DISCORD_MESSAGE_MAX_LENGTH', 2000)
                
                for i in range(0, len(full_message), max_len):
                    chunk = full_message[i:i + max_len]
                    try:
                        await target_channel.send(chunk)
                        await asyncio.sleep(0.5) # Small delay if multiple chunks
                    except discord.Forbidden:
                        logger.error(f"RSS: Bot lacks permissions to post summary in channel {target_channel.name} ({target_channel.id}).")
                        break # Stop trying to send to this channel
                    except Exception as e:
                        logger.error(f"RSS: Error sending summary chunk to {target_channel.name}: {e}", exc_info=True)
                        break
                
                # Clear the articles that were included in this summary
                self.collected_articles_for_summary = self.collected_articles_for_summary[len(articles_to_summarize):]
                # No need to save feeds here, as only collected_articles_for_summary is modified
            else:
                logger.warning("RSS: Gemini returned no content for summary.")
                # Articles remain in the list for the next attempt.

    @check_rss_feeds_loop.before_loop
    @post_hourly_summary_loop.before_loop
    async def before_loops(self):
        await self.bot.wait_until_ready()
        logger.info(f"RSS Cog: Loop '{asyncio.current_task().get_name()}' is ready.")


    # --- Commands (add, remove, list - can remain similar, but 'add' no longer posts directly) ---
    @commands.group(name="rss", aliases=["feed"], invoke_without_command=True, help="Manage RSS feed subscriptions for hourly summaries.")
    @commands.guild_only()
    async def rss_group(self, ctx: commands.Context):
        await ctx.send_help(ctx.command)

    @rss_group.command(name="add", help="Adds an RSS feed to be included in summaries. Usage: !rss add <feed_url> [original_channel_for_errors]")
    @commands.has_permissions(manage_channels=True)
    async def add_feed(self, ctx: commands.Context, feed_url: str, original_channel_for_errors: Optional[discord.TextChannel] = None):
        target_channel_for_errors = original_channel_for_errors or ctx.channel # Where to send add/remove confirmations

        async with self.lock:
            for feed in self.subscribed_feeds:
                if feed.url == feed_url and feed.guild_id == ctx.guild.id: # Only one instance per guild regardless of channel
                    msg = getattr(config, 'RSS_MSG_FEED_ALREADY_EXISTS', "{emoji_error} This RSS feed (`{feed_url}`) is already being monitored for this server.").format(
                        emoji_error=getattr(config, 'RSS_EMOJI_ERROR', '⚠️'), feed_url=feed_url, channel_mention=target_channel_for_errors.mention)
                    await ctx.send(msg); return
        
        try: # Validate feed
            async with aiohttp.ClientSession(headers={'User-Agent': self.user_agent}) as session:
                async with session.get(feed_url, timeout=self.request_timeout) as response:
                    if response.status != 200: raise ValueError(f"HTTP {response.status}")
                    content = await response.text()
                    parsed = await self.bot.loop.run_in_executor(None, feedparser.parse, content)
                    if parsed.bozo or not (parsed.entries or (parsed.feed and parsed.feed.get('title'))):
                        raise ValueError(f"Invalid feed structure. Bozo: {parsed.bozo_exception if parsed.bozo else 'N/A'}")
                    feed_title = parsed.feed.get('title', feed_url)
        except Exception as e:
            logger.warning(f"RSS: Failed to validate feed URL '{feed_url}': {e}")
            await ctx.send(getattr(config, 'RSS_MSG_INVALID_URL', "{emoji_error} Invalid/unreachable RSS URL.").format(emoji_error=getattr(config, 'RSS_EMOJI_ERROR', '⚠️'))); return

        new_feed = RSSFeed(url=feed_url, original_channel_id=target_channel_for_errors.id, guild_id=ctx.guild.id, feed_title=feed_title, added_by=ctx.author.id)
        self.subscribed_feeds.append(new_feed)
        await self._save_feeds()
        
        msg = getattr(config, 'RSS_MSG_FEED_ADDED', "{emoji_success} Added RSS feed: `{feed_url}`. It will be included in hourly summaries.").format(
            emoji_success=getattr(config, 'RSS_EMOJI_SUCCESS', '✅'), feed_url=feed_url, channel_mention=target_channel_for_errors.mention)
        await ctx.send(msg)
        logger.info(f"RSS: Feed '{feed_url}' added by {ctx.author.name} for guild {ctx.guild.id}.")

    @rss_group.command(name="remove", aliases=["delete"], help="Removes an RSS feed from monitoring. Usage: !rss remove <feed_url_or_index>")
    @commands.has_permissions(manage_channels=True)
    async def remove_feed(self, ctx: commands.Context, feed_identifier: str):
        # (Logic similar to previous version, ensures it removes from self.subscribed_feeds and saves)
        feed_to_remove: Optional[RSSFeed] = None
        guild_feeds = [f for f in self.subscribed_feeds if f.guild_id == ctx.guild.id]
        try:
            index = int(feed_identifier) - 1
            if 0 <= index < len(guild_feeds): feed_to_remove = guild_feeds[index]
        except ValueError:
            for feed in guild_feeds:
                if feed.url == feed_identifier: feed_to_remove = feed; break
        
        if feed_to_remove:
            self.subscribed_feeds.remove(feed_to_remove)
            await self._save_feeds()
            await ctx.send(getattr(config, 'RSS_MSG_FEED_REMOVED', "{emoji_success} Removed RSS feed: `{feed_url}`.").format(emoji_success=getattr(config, 'RSS_EMOJI_SUCCESS', '✅'), feed_url=feed_to_remove.url))
        else:
            await ctx.send(getattr(config, 'RSS_MSG_FEED_NOT_FOUND_REMOVE', "{emoji_error} Could not find that RSS feed.").format(emoji_error=getattr(config, 'RSS_EMOJI_ERROR', '⚠️')))

    @rss_group.command(name="list", aliases=["show"], help="Lists RSS feeds being monitored for summaries.")
    @commands.guild_only()
    async def list_feeds(self, ctx: commands.Context):
        # (Logic similar to previous version, lists feeds from self.subscribed_feeds for the current guild)
        guild_feeds = [f for f in self.subscribed_feeds if f.guild_id == ctx.guild.id]
        if not guild_feeds:
            await ctx.send(getattr(config, 'RSS_MSG_NO_FEEDS', "{emoji_info} No RSS feeds are being monitored for summaries in this server.").format(emoji_info=getattr(config, 'RSS_EMOJI_INFO', 'ℹ️'))); return
        embed = discord.Embed(title=getattr(config, 'RSS_MSG_LIST_HEADER', "**Monitored RSS Feeds for Summaries:**"), color=getattr(config, 'RSS_DEFAULT_EMBED_COLOR', discord.Color.blue()))
        desc = ["`{i+1}.` **URL:** <{f.url}> ({f.feed_title or 'N/A'})".format(i=i, f=f) for i, f in enumerate(guild_feeds)]
        embed.description = "\n".join(desc)
        await ctx.send(embed=embed)

    @rss_group.command(name="collectnow", help="Manually triggers article collection from RSS feeds (Owner only).")
    @commands.is_owner()
    async def collect_feeds_now(self, ctx: commands.Context):
        await ctx.send("⚙️ Starting manual article collection from RSS feeds...")
        logger.info(f"Manual RSS article collection triggered by {ctx.author.name}.")
        try:
            await self.check_rss_feeds_loop.coro(self) # Run one cycle of the collection loop
            await ctx.send(f"⚙️ Manual article collection finished. Collected {len(self.collected_articles_for_summary)} articles for the next summary.")
        except Exception as e:
            logger.error(f"Error during manual RSS collection: {e}", exc_info=True)
            await ctx.send(f"⚙️ Manual collection encountered an error: {e}")

    @rss_group.command(name="summarizenow", help="Manually triggers Gemini summary of collected articles (Owner only).")
    @commands.is_owner()
    async def summarize_articles_now(self, ctx: commands.Context):
        await ctx.send("⚙️ Attempting to generate and post news summary now...")
        logger.info(f"Manual RSS summary generation triggered by {ctx.author.name}.")
        try:
            await self.post_hourly_summary_loop.coro(self) # Run one cycle of the summary loop
            # The summary loop sends its own confirmation or "no articles" message.
        except Exception as e:
            logger.error(f"Error during manual RSS summary generation: {e}", exc_info=True)
            await ctx.send(f"⚙️ Summary generation encountered an error: {e}")


    async def cog_unload(self):
        self.check_rss_feeds_loop.cancel()
        if hasattr(self, 'post_hourly_summary_loop') and self.post_hourly_summary_loop.is_running():
            self.post_hourly_summary_loop.cancel()
        logger.info("RSSSummarizer Cog unloaded, loops cancelled.")

    # Error handlers (similar to previous version, adjust as needed)
    @add_feed.error
    @remove_feed.error
    async def rss_modifying_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument): await ctx.send(f"❌ Missing: `{error.param.name}`.")
        elif isinstance(error, commands.ChannelNotFound): await ctx.send(f"❌ Channel not found: {error.argument}")
        elif isinstance(error, commands.MissingPermissions): await ctx.send("❌ No permission (Manage Channels).")
        elif isinstance(error, commands.NoPrivateMessage): await ctx.send("ℹ️ Server only command.")
        else: logger.error(f"RSS cmd error '{ctx.command.name}': {error}", exc_info=True); await ctx.send(f"❗ Error: {error}")
    
    @collect_feeds_now.error
    @summarize_articles_now.error
    async def rss_owner_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.NotOwner): await ctx.send("❌ Owner only command.")
        else: await self.rss_modifying_command_error(ctx, error)


async def setup(bot: commands.Bot):
    if not hasattr(bot, 'gemini_service'):
        logger.critical("RSSCog: Gemini service (`bot.gemini_service`) not found! Summaries will fail. Ensure GeminiService is initialized on the bot instance.")
        # Optionally, don't load the cog or disable summary feature if Gemini is missing
        # For now, it will load but log errors when trying to use Gemini.
    
    feeds_file_path = getattr(config, 'RSS_FEEDS_FILE_PATH', 'data/rss_feeds.json')
    data_dir = os.path.dirname(feeds_file_path)
    if data_dir and not os.path.exists(data_dir):
        try: os.makedirs(data_dir, exist_ok=True)
        except OSError as e: logger.error(f"Could not create dir {data_dir} for RSS: {e}")
    
    await bot.add_cog(RSSCog(bot))
    logger.info("RSSSummarizer Cog (with Gemini) has been setup.")

