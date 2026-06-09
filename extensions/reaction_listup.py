import datetime
import discord
from discord import app_commands
from discord.ext import commands
from daug.utils.dpyexcept import excepter
from daug.utils.dpylog import dpylogger
from utils.database import save_reaction_check


def user_payload(user: discord.User | discord.Member) -> dict:
    return {
        'user_id': str(user.id),
        'name': user.name,
        'display_name': user.display_name,
    }


async def collect_reaction_rows(message: discord.Message) -> list[dict]:
    rows = []
    for reaction in message.reactions:
        reaction_users = [user async for user in reaction.users() if not user.bot]
        reaction_users = sorted(reaction_users, key=lambda user: user.name)
        rows.append({
            'emoji': str(reaction.emoji),
            'count': len(reaction_users),
            'users': [user_payload(user) for user in reaction_users],
        })
    return rows


def reaction_check_document(
    interaction: discord.Interaction,
    message: discord.Message,
    reaction_rows: list[dict],
    checked_at: datetime.datetime,
) -> dict:
    guild = interaction.guild
    channel = interaction.channel
    return {
        'checked_at': checked_at,
        'requested_by_user_id': str(interaction.user.id),
        'requested_by': user_payload(interaction.user),
        'message_author_id': str(message.author.id),
        'message_author': user_payload(message.author),
        'guild_id': str(guild.id) if guild else None,
        'guild_name': guild.name if guild else None,
        'guild_icon_url': str(guild.icon.url) if guild and guild.icon else None,
        'channel_id': str(message.channel.id),
        'channel_name': getattr(channel, 'name', None) or getattr(message.channel, 'name', None),
        'message_id': str(message.id),
        'message_jump_url': message.jump_url,
        'message_created_at': message.created_at,
        'reaction_total': sum(row['count'] for row in reaction_rows),
        'reaction_kind_count': len(reaction_rows),
        'reactions': reaction_rows,
    }


def build_summary_embed(
    interaction: discord.Interaction,
    message: discord.Message,
    reaction_rows: list[dict],
    checked_at: datetime.datetime,
) -> discord.Embed:
    embed = discord.Embed(colour=discord.Colour.yellow(), timestamp=checked_at)
    embed.set_footer(
        text=f'{interaction.guild.name} | {interaction.channel.name}',
        icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
    )
    if not reaction_rows:
        embed.description = 'リアクションはありません。'
        return embed

    for row in reaction_rows:
        if len(row['users']) > 10:
            continue
        embed.add_field(
            name=f'{row["emoji"]}({row["count"]})',
            value='\n'.join([
                f'<@{user["user_id"]}> {user["display_name"].replace("`", "")} `{user["name"]}`'
                for user in row['users']
            ]) or 'リアクションしたユーザーはいません',
            inline=False,
        )
    return embed


async def send_large_reaction_dm(
    interaction: discord.Interaction,
    message: discord.Message,
    reaction_row: dict,
    checked_at: datetime.datetime,
) -> None:
    large_embeds = []
    users = reaction_row['users']
    for n in range(len(users) // 25 + 1):
        display_users = users[n * 25: n * 25 + 25]
        if not display_users:
            continue
        large_embed = discord.Embed(
            title=f'{reaction_row["emoji"]} {reaction_row["count"]}',
            colour=discord.Colour.yellow(),
            timestamp=checked_at,
        )
        for display_user in display_users:
            large_embed.add_field(
                name=display_user['display_name'],
                value=f'<@{display_user["user_id"]}> {display_user["name"]}',
                inline=True,
            )
        large_embed.set_footer(
            text=f'{interaction.guild.name} | {interaction.channel.name}',
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
        )
        large_embeds.append(large_embed)
        if len(large_embeds) >= 4:
            await interaction.user.send(
                f'{message.jump_url} {reaction_row["emoji"]}',
                embeds=large_embeds,
            )
            large_embeds = []
    if large_embeds:
        await interaction.user.send(
            f'{message.jump_url} {reaction_row["emoji"]}',
            embeds=large_embeds,
        )


class ReactionListCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name='リアクション確認',
            callback=self._listup_reaction_app_command,
        )
        self.bot.tree.add_command(self.ctx_menu)

    @app_commands.guild_only()
    @excepter
    @dpylogger
    async def _listup_reaction_app_command(self, interaction: discord.Interaction, message: discord.Message):
        if message.author != interaction.user:
            await interaction.response.send_message('自分のメッセージのみ確認することができます', ephemeral=True)
            return
        await interaction.response.send_message('リアクション確認結果を保存し、DMにも送信します', ephemeral=True)
        now_jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        reaction_rows = await collect_reaction_rows(message)
        await save_reaction_check(
            reaction_check_document(interaction, message, reaction_rows, now_jst),
        )

        for reaction_row in reaction_rows:
            if len(reaction_row['users']) > 10:
                await send_large_reaction_dm(interaction, message, reaction_row, now_jst)

        summary_embed = build_summary_embed(interaction, message, reaction_rows, now_jst)
        if summary_embed.fields or summary_embed.description:
            await interaction.user.send(message.jump_url, embed=summary_embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReactionListCog(bot))
