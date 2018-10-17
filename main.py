import discord
import asyncio
import bot
import commands
from sqlalchemy import text
from singletons.disc import Discord_bot
from database.db import Database
from database.models import Scrims, Servers
import config as cfg
from datetime import datetime, timedelta
from pytz import timezone
import embeds
import teamup

disc = Discord_bot()
client = disc.get_client()

bot = bot.Scrim_bot()

bot.commands.append(commands.Setup())
bot.commands.append(commands.AddScrim())
bot.commands.append(commands.DeleteScrim())
bot.commands.append(commands.EditScrim())
bot.commands.append(commands.UpdateSchedule())
bot.commands.append(commands.TeamupSetup())

#if cfg.bot["version"] == "dev":
#    bot.commands.append(commands.StopCommand())

db = Database()

# loop checking for reminders / updates
async def periodic():
    while True:
        utc_now = datetime.now(timezone("UTC"))
        utc_now_15min = utc_now + timedelta(minutes=15)
        fmt_date = "%Y-%m-%d"
        fmt = "%H:%M"
        # get all scrims that are happening in ~15 minutes
        with db.connect() as session:
            scrims = session.query(Scrims).filter(Scrims.time_start <= utc_now_15min).filter(Scrims.notified == False).all()
            session.expunge_all()

        for scrim in scrims:
            scrim = scrim.as_dict()
            with db.connect() as session:
                server = session.query(Servers).filter(Servers.discord_server_id == scrim["discord_server_id"]).first()
                session.expunge_all()

            if server is not None:
                sd = server.as_dict()
                # timezones stuff
                server_tz = timezone(sd["timezone"])
                utc_tz = timezone("UTC")
                utc_tz.localize(scrim["time_start"])
                utc_tz.localize(scrim["time_end"])

                time_start_server = scrim["time_start"].astimezone(server_tz)
                time_end_server = scrim["time_end"].astimezone(server_tz)
                # Embed to inform people assembling
                embed = embeds.Info("Scrim happening", "There is a scrim happening in less than 15 minutes")
                embed.set_thumbnail(url="http://bot.patrikpapso.com/swords.png")
                embeds.add_embed_footer(embed)
                embed.add_field(name="Date", value=time_start_server.strftime(fmt_date), inline=False)
                embed.add_field(name="Start of the scrim",value=time_start_server.strftime(fmt),inline=True)
                embed.add_field(name="End of the scrim",value=time_end_server.strftime(fmt),inline=True)
                embed.add_field(name="Timezone", value=time_start_server.tzinfo, inline=True)
                embed.add_field(name="Opponent", value=scrim["enemy_team"], inline=True)
                # send embed to reminder channel
                await disc.send_message(discord.Object(sd["channel_id_reminder"]), content="<@&%s>" % sd["mention_role"], embed=embed)
        # set all scrims to notified = True
        with db.connect() as session:
            scrims = session.query(Scrims).filter(Scrims.time_start <= utc_now_15min).\
                                           filter(Scrims.notified == False).\
                                           update({"notified": True})
            session.expunge_all()

        await asyncio.sleep(300)  # do every 5 minutes

@client.event
async def on_ready():
    print("Logged in as")
    print(client.user.name)
    print(client.user.id)
    print("------")
    client.loop.create_task(periodic())

# on message go through registered commands
@client.event
async def on_message(message):
    for command in bot.commands:
        if message.content.startswith(command.activation_string):
            vals = message.content.split(" ")
            if(len(vals) > 1):
                if vals[1] == "help":
                    await command.help(message)
                    return

            await command.action(bot, message)
            return

client.run( cfg.bot["prod_token"] if cfg.bot["version"] == "prod" else cfg.bot["dev_token"])