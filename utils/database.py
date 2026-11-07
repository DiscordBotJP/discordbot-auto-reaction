from cloudflare_storage import create_client
from caches import emojis_cache
from constants import DATABASE_PROVIDER, MONGO_URL

client = create_client(MONGO_URL)
database = client.auto_reaction
# database_emojis = database.emojis


async def cache_emojis() -> None:
    async for emojis in database.emojis.find():
        channel_id = emojis.get('channel_id')
        emojis = emojis.get('emojis')
        emojis_cache[channel_id] = emojis


async def ensure_reaction_check_indexes() -> None:
    # D1 indexes are deployed with the data-service schema, not created by Bots.
    if DATABASE_PROVIDER == 'd1':
        return
    await database.reaction_checks.create_index([
        ('requested_by_user_id', 1),
        ('checked_at', -1),
    ])
    await database.reaction_checks.create_index([
        ('message_id', 1),
        ('requested_by_user_id', 1),
    ])


def get_emojis(channel_id: int) -> dict | None:
    return emojis_cache.get(channel_id)


async def upsert_emojis(channel_id: int, emojis: list[str]) -> bool:
    query = {'channel_id': channel_id}
    values = {
        'channel_id': channel_id,
        'emojis': emojis,
    }
    await database.emojis.update_one(query, {'$set': values}, upsert=True)
    emojis_cache[channel_id] = emojis


async def delete_emojis(channel_id):
    result = await database.emojis.delete_one({'channel_id': channel_id})
    if result.deleted_count > 0:
        emojis_cache.pop(channel_id, None)


async def save_reaction_check(reaction_check: dict) -> str:
    result = await database.reaction_checks.insert_one(reaction_check)
    return str(result.inserted_id)
