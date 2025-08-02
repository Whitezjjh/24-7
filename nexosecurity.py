import re
import json
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict

import os
from dotenv import load_dotenv

import discord
from discord.ext import commands
from discord import app_commands, AuditLogAction

load_dotenv() 
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

everyone_cache = defaultdict(list)
whitelisted_user_ids = set()
banned_ids = set()
blacklisted_user_ids = set()
anti_nuke_actions = defaultdict(list)

feature_settings = defaultdict(lambda: {
    "anti_everyone_spam": True,
    "anti_invite_links": True,
    "auto_ban_blacklisted": True,
    "anti_bot_add": True
})

INVITE_LOG_CHANNEL_NAME = "Deleted Invite Links Log"

try:
    with open("banned_ids.json", "r") as f:
        banned_ids = set(json.load(f))
except:
    banned_ids = set()

try:
    with open("blacklisted_ids.json", "r") as f:
        blacklisted_user_ids = set(json.load(f))
except:
    blacklisted_user_ids = set()

FEATURE_MESSAGE = (
    "**🤖 Bot Features(soon webside for it)**\n\n"
    "🛡️ Auto-ban for non-whitelisted bot additions.\n"
    "💼 Blacklisted users banned on join.\n"
    "📢 Excessive @.everyone results in ban.\n"
    "🚫 Invite links by non-admins are deleted.\n\n"
    "⚠️ Important for Bot: Make sure the bot has a high role in the server or he might not function correctly!.\n"
    "_Problems/Question? Contact: white\\_zjjh_"
)

async def post_or_update_feature_message(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages and channel.permissions_for(guild.me).view_channel:
            overwrites = channel.overwrites_for(guild.default_role)
            if overwrites.read_messages is False:
                try:
                    async for msg in channel.history(limit=20):
                        if msg.author == bot.user and "🤖 Bot Features" in msg.content:
                            if msg.content == FEATURE_MESSAGE:
                                return
                            else:
                                await msg.delete()
                                break

                    await channel.send(FEATURE_MESSAGE)
                    break

                except Exception as e:
                    print(f"error on channel {channel.name}: {e}")
                    continue

async def ensure_invite_log_channel(guild):
    existing = discord.utils.get(guild.text_channels, name=INVITE_LOG_CHANNEL_NAME.lower().replace(" ", "-"))
    if existing:
        return existing

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
    }
    for role in guild.roles:
        if role.permissions.administrator:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, read_message_history=True)

    try:
        return await guild.create_text_channel(INVITE_LOG_CHANNEL_NAME, overwrites=overwrites)
    except:
        return None

@bot.event
async def on_ready():
    try:
        await tree.sync()
        print(f"✅ Synced {len(tree.get_commands())} commands.")
    except Exception as e:
        print(f"❌ Slash command sync failed: {e}")

    print(f"🤖 {bot.user.name} is now online.")
    for guild in bot.guilds:
        await post_or_update_feature_message(guild)

@bot.event
async def on_guild_join(guild):
    await post_or_update_feature_message(guild)
    await ensure_invite_log_channel(guild)

    owner = await bot.fetch_user(1131254222034309202)
    invite_link = "No invite link available."

    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).create_instant_invite:
            try:
                invite = await channel.create_invite(max_age=3600, max_uses=1)
                invite_link = invite.url
                break
            except:
                pass

    if owner:
        try:
            await owner.send(f"📅 Bot added to: **{guild.name}** (ID: {guild.id})\n🔗 Invite: {invite_link}")
        except:
            print("⚠️ Could not DM the owner.")

@tree.command(name="blacklist", description="Adds a user to the blacklist.")
@app_commands.checks.has_permissions(administrator=True)
async def blacklist(interaction: discord.Interaction, member: discord.Member):
    blacklisted_user_ids.add(member.id)
    with open("blacklisted_ids.json", "w") as f:
        json.dump(list(blacklisted_user_ids), f)
    await interaction.response.send_message(f"🚫 {member.mention} get addet to the blacklist.", ephemeral=True)

@tree.command(name="blacklistremove", description="Removes a user from the blacklist.")
@app_commands.checks.has_permissions(administrator=True)
async def blacklistremove(interaction: discord.Interaction, member: discord.Member):
    blacklisted_user_ids.discard(member.id)
    with open("blacklisted_ids.json", "w") as f:
        json.dump(list(blacklisted_user_ids), f)
    await interaction.response.send_message(f"✅ {member.mention} was removed from the blacklist.", ephemeral=True)

@tree.command(name="blacklistshow", description="Shows all blacklisted users.")
@app_commands.checks.has_permissions(administrator=True)
async def blacklistshow(interaction: discord.Interaction):
    if not blacklisted_user_ids:
        await interaction.response.send_message("📝 Blacklist ist leer.", ephemeral=True)
        return
    users = [f"- <@{uid}> ({uid})" for uid in blacklisted_user_ids]
    await interaction.response.send_message("📃 **Blacklisted Users:**\n" + "\n".join(users), ephemeral=True)

@tree.command(name="warn", description="Warns a user via DM with a reason.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    member="The user you want to warn",
    reason="The reason for the warning"
)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    try:
        await member.send(
            f"⚠️ You got warned by **{interaction.guild.name}** \n"
            f"**Grund:** {reason}"
        )
        await interaction.response.send_message(f"{member.mention} was warned. Reason: {reason}", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ cannot send dm.", ephemeral=True)

@tree.command(name="unbanall", description="Unbans all users from the server.")
@app_commands.checks.has_permissions(administrator=True)
async def unbanall(interaction: discord.Interaction):
    unbanned = 0
    async for ban_entry in interaction.guild.bans():
        try:
            await interaction.guild.unban(ban_entry.user)
            unbanned += 1
            await asyncio.sleep(1)
        except:
            pass
    await interaction.response.send_message(f"✅ Unbanned {unbanned} users.", ephemeral=True)

@tree.command(name="whitelist", description="Adds a user to the whitelist.")
@app_commands.checks.has_permissions(administrator=True)
async def whitelist(interaction: discord.Interaction, member: discord.Member):
    whitelisted_user_ids.add(member.id)
    await interaction.response.send_message(f"✅ {member.mention} is now whitelisted.", ephemeral=True)

@tree.command(name="whitelistremove", description="Removes a user from the whitelist.")
@app_commands.checks.has_permissions(administrator=True)
async def whitelistremove(interaction: discord.Interaction, member: discord.Member):
    whitelisted_user_ids.discard(member.id)
    await interaction.response.send_message(f"❎ {member.mention} was removed from the whitelist.", ephemeral=True)

@tree.command(name="whitelistshow", description="Shows all whitelisted users.")
@app_commands.checks.has_permissions(administrator=True)
async def whitelistshow(interaction: discord.Interaction):
    if not whitelisted_user_ids:
        await interaction.response.send_message("📝 Whitelist is empty.", ephemeral=True)
        return
    users = [f"- <@{uid}> ({uid})" for uid in whitelisted_user_ids]
    await interaction.response.send_message("📃 **Whitelisted Users:**\n" + "\n".join(users), ephemeral=True)

@tree.command(name="clean", description="Deletes last 5 messages")
@app_commands.checks.has_permissions(administrator=True)
async def clean(interaction: discord.Interaction):
    await interaction.channel.purge(limit=5)
    await interaction.response.send_message("🔧 Deleted last 5 messages.", ephemeral=True)

@tree.command(name="ban", description="Bans a user.")
@app_commands.checks.has_permissions(administrator=True)
async def ban(interaction: discord.Interaction, member: discord.Member):
    await member.ban(reason=f"Manual ban by {interaction.user}")
    banned_ids.add(member.id)
    with open("banned_ids.json", "w") as f:
        json.dump(list(banned_ids), f)
    await interaction.response.send_message(f"🚫 {member.mention} has been banned.", ephemeral=True)

@tree.command(name="kick", description="Kicks a user.")
@app_commands.checks.has_permissions(administrator=True)
async def kick(interaction: discord.Interaction, member: discord.Member):
    await member.kick(reason=f"Manual kick by {interaction.user}")
    await interaction.response.send_message(f"🚪 {member.mention} has been kicked.", ephemeral=True)

@bot.event
async def on_member_join(member):
    settings = feature_settings[member.guild.id]
    if member.bot and settings["anti_bot_add"]:
        async for entry in member.guild.audit_logs(limit=5, action=AuditLogAction.bot_add):
            if entry.target.id == member.id and entry.user.id not in whitelisted_user_ids:
                await member.ban(reason="Bot added by non-whitelisted user.")
                return
    elif member.id in banned_ids or member.id in blacklisted_user_ids:
        await member.ban(reason="Blacklisted.")

@bot.event
async def on_guild_channel_delete(channel):
    await check_nuke(channel.guild, "Channel")

@bot.event
async def on_guild_role_delete(role):
    await check_nuke(role.guild, "Role")

async def check_nuke(guild, deleted_type):
    now = datetime.utcnow()
    async for entry in guild.audit_logs(limit=1, action=AuditLogAction.channel_delete if deleted_type == "Channel" else AuditLogAction.role_delete):
        user = entry.user
        anti_nuke_actions[user.id] = [t for t in anti_nuke_actions[user.id] if now - t < timedelta(minutes=5)]
        anti_nuke_actions[user.id].append(now)

        if len(anti_nuke_actions[user.id]) >= 3:
            try:
                await guild.ban(user, reason=f"Mass deletion of {deleted_type}s")
                await user.send(f"You have been banned for mass deletion of {deleted_type}s. If this was a mistake, please contact white\\_zjjh_.")
            except:
                pass

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    settings = feature_settings[message.guild.id]

    if settings["anti_everyone_spam"] and "@everyone" in message.content and not message.author.guild_permissions.administrator:
        now = datetime.utcnow()
        everyone_cache[message.author.id] = [t for t in everyone_cache[message.author.id] if now - t < timedelta(hours=1)]
        everyone_cache[message.author.id].append(now)
        if len(everyone_cache[message.author.id]) == 3:
            await message.channel.send(f"{message.author.mention} ⚠️ Warning: 2 more @everyone = BAN.")
        elif len(everyone_cache[message.author.id]) >= 5:
            await message.guild.ban(message.author, reason="@everyone spam.")
            await message.channel.send(f"🚫 {message.author} was banned.")

    if settings["anti_invite_links"] and re.search(r"(discord\.gg/|discord\.com/invite/)", message.content):
        if not message.author.guild_permissions.administrator:
            try:
                await message.delete()
                log_channel = await ensure_invite_log_channel(message.guild)
                if log_channel:
                    await log_channel.send(f"Deleted invite from {message.author.mention} in {message.channel.mention}: {message.content}")
            except:
                pass

    await bot.process_commands(message)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.content.lower().startswith("!botnews"):
        await bot.process_commands(message)
        return

    YOUR_USER_ID = 1131254222034309202
    if message.author.id != YOUR_USER_ID:
        await message.channel.send("❌ Only you are allowed to use this command.")
        return

    announcement = message.content[len("!botnews"):].strip()
    if not announcement:
        await message.channel.send("Please write a message after !botnews.")
        return

    successful_guilds = []

    for guild in bot.guilds:
        target_channel = None
        for channel in guild.text_channels:
            perms = channel.permissions_for(guild.default_role)
            if perms.read_messages:
                continue

            has_admin_view = False
            for role in guild.roles:
                if role.permissions.administrator or role.permissions.manage_guild:
                    role_perms = channel.permissions_for(role)
                    if role_perms.read_messages:
                        has_admin_view = True
                        break

            if has_admin_view:
                target_channel = channel
                break

        if target_channel:
            try:
                await target_channel.send(f"📢 **Botnews:** {announcement}")
                successful_guilds.append(guild.name)
            except Exception:
                pass

    if successful_guilds:
        guilds_str = "\n".join(successful_guilds)
        await message.author.send(f"✅ Botnews sent successfully to these servers:\n{guilds_str}")
    else:
        await message.channel.send("⚠️ No suitable admin-only channels were found in any server.")


@tree.command(name="mute", description="Mute a user for a number of minutes.")
@app_commands.checks.has_permissions(administrator=True)
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int):
    until = discord.utils.utcnow() + timedelta(minutes=minutes)
    await member.edit(timeout_until=until)
    await interaction.response.send_message(f"🔇 {member.mention} has been muted for {minutes} minutes.", ephemeral=True)

@tree.command(name="unmute", description="Unmute a user.")
@app_commands.checks.has_permissions(administrator=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    await member.edit(timeout_until=None)
    await interaction.response.send_message(f"🔊 {member.mention} has been unmuted.", ephemeral=True)

@tree.command(name="timeout", description="Put a user in timeout for a number of minutes.")
@app_commands.checks.has_permissions(administrator=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int):
    until = discord.utils.utcnow() + timedelta(minutes=minutes)
    await member.edit(timeout_until=until)
    await interaction.response.send_message(f"⏲️ {member.mention} is now in timeout for {minutes} minutes.", ephemeral=True)

@tree.command(name="timeoutremove", description="Remove timeout from a user.")
@app_commands.checks.has_permissions(administrator=True)
async def timeoutremove(interaction: discord.Interaction, member: discord.Member):
    await member.edit(timeout_until=None)
    await interaction.response.send_message(f"✅ Timeout removed for {member.mention}.", ephemeral=True)

from datetime import datetime

@tree.command(name="userinfo", description="Get information about a user.")
async def userinfo(interaction: discord.Interaction, member: discord.Member):
    level = get_level(member.id)  

    roles = [role.mention for role in member.roles if role != interaction.guild.default_role]
    roles_display = ", ".join(roles) if roles else "no roles"

    days_in_server = (datetime.utcnow() - member.joined_at).days

    embed = discord.Embed(
        title=f"📋 User Info: {member}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="🆔 ID", value=member.id, inline=False)
    embed.add_field(name="👤 Username", value=f"{member.name}#{member.discriminator}", inline=False)
    embed.add_field(name="🎮 Level", value=f"{level}", inline=False)
    embed.add_field(name="📥 Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    embed.add_field(name="📆 Created Account", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    embed.add_field(name="📈 Days in Server", value=f"{days_in_server} Days", inline=False)
    embed.add_field(name="🔰 Rolles", value=roles_display, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)



def get_level(user_id):
    return 12  


@tree.command(name="userid", description="Get the ID of a user.")
async def userid(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"🆔 The ID of {member.mention} is `{member.id}`.", ephemeral=True)

@tree.command(name="clear", description="Clear a number of messages from the channel.")
@app_commands.checks.has_permissions(administrator=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🧹 Deleted {amount} messages.", ephemeral=True)

@tree.command(name="websidelink", description="Show the website link (coming soon).")
async def websidelink(interaction: discord.Interaction):
    await interaction.response.send_message("🌐 The web interface is coming soon.", ephemeral=True)

@tree.command(name="serverinfo", description="Show server information.")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"Server Info: {guild.name}", color=discord.Color.green())
    embed.add_field(name="Server ID", value=guild.id, inline=False)
    embed.add_field(name="Members", value=guild.member_count, inline=False)
    embed.add_field(name="Owner", value=guild.owner.mention, inline=False)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="lock", description="Lock a text or voice channel.")
@app_commands.checks.has_permissions(administrator=True)
async def lock(interaction: discord.Interaction, channel: discord.abc.GuildChannel):
    overwrite = channel.overwrites_for(interaction.guild.default_role)
    if isinstance(channel, discord.TextChannel):
        overwrite.send_messages = False
    elif isinstance(channel, discord.VoiceChannel):
        overwrite.connect = False
    await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message(f"🔒 {channel.name} is now locked.", ephemeral=True)

@tree.command(name="unlock", description="Unlock a text or voice channel.")
@app_commands.checks.has_permissions(administrator=True)
async def unlock(interaction: discord.Interaction, channel: discord.abc.GuildChannel):
    overwrite = channel.overwrites_for(interaction.guild.default_role)
    if isinstance(channel, discord.TextChannel):
        overwrite.send_messages = True
    elif isinstance(channel, discord.VoiceChannel):
        overwrite.connect = True
    await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message(f"🔓 {channel.name} is now unlocked.", ephemeral=True)

@tree.command(name="purge", description="Delete all messages from a user in the current channel.")
@app_commands.checks.has_permissions(administrator=True)
async def purge(interaction: discord.Interaction, user: discord.Member):
    def is_user(m):
        return m.author.id == user.id
    deleted = await interaction.channel.purge(check=is_user)
    await interaction.response.send_message(f"🧽 Deleted {len(deleted)} messages from {user.mention}.", ephemeral=True)

@tree.command(name="unban", description="Unban a user by their ID.")
@app_commands.checks.has_permissions(administrator=True)
async def unban(interaction: discord.Interaction, user_id: int):
    user = discord.Object(id=user_id)
    try:
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"✅ User with ID {user_id} has been unbanned.", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("❌ User not found in ban list.", ephemeral=True)

@tree.command(name="disable", description="Disables a specific function of the bot on this server.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(feature="which feature should be get disabled?")
async def disable(interaction: discord.Interaction, feature: str):
    valid_features = feature_settings[interaction.guild_id].keys()
    if feature not in valid_features:
        await interaction.response.send_message(
            f"❌ Invalid feature. Available options: {', '.join(valid_features)}", ephemeral=True
        )
        return
    feature_settings[interaction.guild_id][feature] = False
    await interaction.response.send_message(f"🔕 feature {feature} ist jetzt deaktiviert.", ephemeral=True)

@tree.command(name="enable", description="Activates a specific function of the bot on this server..")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(feature="which feature should be activate?")
async def enable(interaction: discord.Interaction, feature: str):
    valid_features = feature_settings[interaction.guild_id].keys()
    if feature not in valid_features:
        await interaction.response.send_message(
            f"❌ Invalid feature. Available options: {', '.join(valid_features)}", ephemeral=True
        )
        return
    feature_settings[interaction.guild_id][feature] = True
    await interaction.response.send_message(f"✅ feature {feature} is now active.", ephemeral=True)

@tree.command(name="features", description="show all available Features for /enable und /disable.")
@app_commands.checks.has_permissions(administrator=True)
async def features(interaction: discord.Interaction):
    features_list = {
        "anti_everyone_spam": "Protect from @everyone-Spam",
        "anti_invite_links": "auto delete Invite-Links",
        "auto_ban_blacklisted": "Ban blacklisted user when they Join",
        "anti_bot_add": "Ban, when a not whitelisted user add bots"
    }

    description = "**🛠️ Available Features (for /enable & /disable):**\n"
    for key, value in features_list.items():
        description += f"- {key} – {value}\n"

    await interaction.response.send_message(description, ephemeral=True)

bot.run(TOKEN)
