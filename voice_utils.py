import discord


def get_voice_client_for_guild(bot_client, guild):
    return discord.utils.get(bot_client.voice_clients, guild=guild)
