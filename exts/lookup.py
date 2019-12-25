"""
Lookup extension for qrm
---
Copyright (C) 2019 Abigail Gold, 0x5c

This file is part of discord-qrm2 and is released under the terms of the GNU
General Public License, version 2.
"""

import threading
import re
import json
from datetime import datetime

from discord.ext import commands, tasks
from ctyparser import BigCty

import common as cmn


class LookupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = bot.qrm.session
        self.sat_list = []
        try:
            self.cty = BigCty('./data/cty.json')
        except OSError:
            self.cty = BigCty()

    @commands.command(name="sat", category=cmn.cat.lookup)
    async def _sat_lookup(self, ctx: commands.Context, sat_name: str, grid1: str, grid2: str = None):
        '''Links to info about satellite passes on satmatch.com.'''
        now = datetime.utcnow().strftime('%Y-%m-%d%%20%H:%M')
        await ctx.send(len(self.sat_list))
        # if grid2 is None or grid2 == '':
        #     await ctx.send(f'http://www.satmatch.com/satellite/{sat_name}/obs1/{grid1}'
        #                    f'?search_start_time={now}&duration_hrs=24')
        # else:
        #     await ctx.send(f'http://www.satmatch.com/satellite/{sat_name}/obs1/{grid1}'
        #                    f'/obs2/{grid2}?search_start_time={now}&duration_hrs=24')

    @commands.command(name="dxcc", aliases=['dx'], category=cmn.cat.lookup)
    async def _dxcc_lookup(self, ctx: commands.Context, query: str):
        '''Gets info about a DXCC prefix.'''
        with ctx.typing():
            query = query.upper()
            full_query = query
            embed = cmn.embed_factory(ctx)
            embed.title = f'DXCC Info for '
            embed.description = f'*Last Updated: {self.cty.formatted_version}*'
            embed.colour = cmn.colours.bad
            while query:
                if query in self.cty.keys():
                    data = self.cty[query]
                    embed.add_field(name="Entity",
                                    value=data['entity'])\
                         .add_field(name="CQ Zone",
                                    value=data['cq'])\
                         .add_field(name="ITU Zone",
                                    value=data['itu'])\
                         .add_field(name="Continent",
                                    value=data['continent'])\
                         .add_field(name="Time Zone",
                                    value=f'+{data["tz"]}' if data['tz'] > 0 else str(data['tz']))
                    embed.title += query
                    embed.colour = cmn.colours.good
                    break
                else:
                    query = query[:-1]
            else:
                embed.title += full_query + ' not found'
                embed.colour = cmn.colours.bad
        await ctx.send(embed=embed)

    @tasks.loop(minutes=1)
    async def _get_sats(self):
        url = 'https://www.satmatch.com/static/nasabare.txt'
        sats = []
        async with self.session.get(url) as resp:
            if resp.status != 200:
                print('[**] Could not load list of satellites')
                return False
            sats_raw = await resp.text()
        for line in sats_raw:
            # remove non-name data
            if line[0] not in '12' and line[1] != ' ':
                # remove erroring satellite names
                # if ' ' in line or '/' in line:
                sats.append(line.strip())
        self.sat_list = sats

    @tasks.loop(hours=24)
    async def _update_cty(self):
        update = threading.Thread(target=run_update, args=(self.cty, "./data/cty.json"))
        update.start()


def run_update(cty_obj, dump_loc):
    update = cty_obj.update()
    if update:
        cty_obj.dump(dump_loc)


def setup(bot: commands.Bot):
    lookupcog = LookupCog(bot)
    bot.add_cog(lookupcog)
    lookupcog._update_cty.start()
    lookupcog._get_sats.start()
