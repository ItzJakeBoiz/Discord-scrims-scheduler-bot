import discord
from singletons.disc import Discord_bot
import random
from datetime import datetime, timedelta
from pytz import timezone, all_timezones
from database.models import Servers, Scrims
from database.db import Database
import embeds


disc = Discord_bot()
client = disc.get_client()

db = Database()

class Scrim_bot:
    commands = []

    async def setup(self, message):
        '''
		    Command: !setup [timezone] [owner] [mention] [schedule-channel] [reminder-channel]
              vals -    0       1
            Whole setup is contained in one command to keep it simple
        '''
        vals = message.content.split(" ")
        if vals[1] in all_timezones:
            # Check if 2 roles were mentioned 0 - owner, 1 - reminders
            role_mentions = message.role_mentions
            if len(role_mentions) == 2:
                # Check if 2 channels were mentioned 0 - schedule, 1 - reminders
                channel_mentions = message.channel_mentions
                if len(channel_mentions) == 2:
                    message = await disc.send_message(channel_mentions[0], "kek")
                    # Save server data to server for future use
                    with db.connect() as session:
                        server = Servers(message.server.id, message.server.name, vals[1], role_mentions[0].id, role_mentions[1].id, channel_mentions[0].id, channel_mentions[1].id, message.id)
                        session.add(server)
                else:
                    await disc.send_message(message.channel, embed=embeds.Error("Wrong arguments", "You need to provide 2 channel (schedule + reminders)"))
            else:
                await disc.send_message(message.channel, embed=embeds.Error("Wrong arguments", "You need to provide 2 mentionable roles (owner + reminder)"))
        else:
            await disc.send_message(message.channel, embed=embeds.Error("Wrong arguments", "Unknown timezone, try to use this [LINK](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) for reference."))

    async def add_scrim(self, message):
        '''
           Command: !scrimsadd [dd/mm] [hh:mm] [hh:mm] [enemy-team-name]
              vals -    0         1       2       3            4
           Creates a new scrim entry, replies with embed containing information about added scrim
        '''
        vals = message.content.split(" ")
        if len(vals) == 5:
            with db.connect() as session:
                query = (
                    session.query(Servers)
                    .filter_by(discord_server_id=message.server.id)
                    .first()
                )
                session.expunge_all()

            server_data = query.as_dict()
            # parse date
            dt_now = datetime.now()
            date = vals[1].split("/")
            # this format has to be mm/dd/yyyy
            scrim_date = "{}/{}/{}".format(date[1], date[0], dt_now.year)
                # TODO: Implement ability to add scrims for next year
                # Just check for date being in the past, if it's in the past, it's happening next year
            # datetime formatting
            fmt = "%H:%M"
            fmt_date = "%Y-%m-%d"
            server_tz = timezone(server_data["timezone"]) 
            utc_tz = timezone("UTC")
            # ugly time formatting practice
            ts = vals[2].split(":") # time-start
            te = vals[3].split(":") # time-end
            # localize this datetime to server's timezone
            time_start_tz = server_tz.localize(datetime(dt_now.year, int(date[1]), int(date[0]), int(ts[0]), int(ts[1]), 0))
            time_end_tz   = server_tz.localize(datetime(dt_now.year, int(date[1]), int(date[0]), int(te[0]), int(te[1]), 0))
            # localize these datetimes to UTC for database storage
            utc_ts = time_start_tz.astimezone(utc_tz)
            utc_te = time_end_tz.astimezone(utc_tz)
            # parse enemy-team-name
            enemy_team_name = " ".join(str(x) for x in vals[4:])
            # save the entry into database
            with db.connect() as session:
                scrim = Scrims(message.server.id, scrim_date, utc_ts, utc_te, enemy_team_name)
                session.add(scrim)

                # TODO: Add this scrim to TeamUp database

        else:
            await disc.send_message(message.channel, embed=embeds.Error("Wrong arguments", "Wrong argument provided, user `!scrimsadd help` for help"))          
            return

    async def update_schedule(self, message):
        today = datetime.today()
        week_from_today = today + timedelta(days=7)

        with db.connect() as session:
                query = (
                    session.query(Servers)
                    .filter(Servers.discord_server_id == message.server.id)
                    .first()
                )
                session.expunge_all()
        print(query)
        if query is not None:
            server_data = query.as_dict()
            schedule_embed = embeds.get_schedule_embed(today, week_from_today, server_data["discord_server_id"], server_data["timezone"])
            msg = await disc.get_message(discord.Object(server_data["channel_id_schedule"]), server_data["message_id_schedule"])
            if msg is not None:
                await disc.edit_message(msg, embed=schedule_embed)
        else:
            return None

          