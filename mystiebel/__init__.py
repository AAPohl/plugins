#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2020-      <AUTHOR>                                  <EMAIL>
#########################################################################
#  This file is part of SmartHomeNG.
#  https://www.smarthomeNG.de
#  https://knx-user-forum.de/forum/supportforen/smarthome-py
#
#  Sample plugin for new plugins to run with SmartHomeNG version 1.10
#  and up.
#
#  SmartHomeNG is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHomeNG is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHomeNG. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

import asyncio
import aiohttp

from lib.model.smartplugin import SmartPlugin
from lib.item import Items

from .pystiebel import *

from .webif import WebInterface

class myStiebel(SmartPlugin):

    PLUGIN_VERSION = '1.0.0'

    def __init__(self, sh):
        super().__init__()

        self.username = self.get_parameter_value('username')
        self.password = self.get_parameter_value('password')

        # Some Id: Fix, but different for each instance
        self.client_id = "3f2504e0-4f89-41d3-9a0c-0405e82c3301"
        self.logger.debug(f"Client_Id: {self.client_id}")

        self.sensor_ids = []
        self.itemlist = []

        self.init_webinterface(WebInterface)

        return

    def run(self):
        self.logger.debug("myStiebel Plugin started")
        self.start_asyncio(self.plugin_coro())

    def stop(self):
        self.alive = False
        self.stop_asyncio()

    def parse_item(self, item):
        if self.has_iattr(item.conf, 'mystiebel_sensor'):
            sensor_id = item.conf['mystiebel_sensor']
            if sensor_id not in self.sensor_ids:
                self.sensor_ids.append(sensor_id)
            if item not in self.itemlist:
                self.itemlist.append(item)
            self.logger.debug(f"Registered sensor_id {sensor_id} from item {item.property.path}")
            return self.update_item

    def parse_logic(self, logic):
        pass

    def update_item(self, item, caller=None, source=None, dest=None):
        """
        Item has been updated

        This method is called, if the value of an item has been updated by SmartHomeNG.
        It should write the changed value out to the device (hardware/interface) that
        is managed by this plugin.

        To prevent a loop, the changed value should only be written to the device, if the plugin is running and
        the value was changed outside of this plugin(-instance). That is checked by comparing the caller parameter
        with the fullname (plugin name & instance) of the plugin.

        :param item: item to be updated towards the plugin
        :param caller: if given it represents the callers name
        :param source: if given it represents the source
        :param dest: if given it represents the dest
        """
        # check for pause item
        if item is self._pause_item:
            if caller != self.get_shortname():
                self.logger.debug(f'pause item changed to {item()}')
                if item() and self.alive:
                    self.stop()
                elif not item() and not self.alive:
                    self.run()
            return

        if self.alive and caller != self.get_fullname():
            # code to execute if the plugin is not stopped
            # and only, if the item has not been changed by this plugin:
            self.logger.info(f"update_item: '{item.property.path}' has been changed outside this plugin by caller '{self.callerinfo(caller, source)}'")

            pass

    def poll_device(self):
        pass

    async def plugin_coro(self):
        self.logger.notice("plugin_coro started")

        self.alive = True

        try:
            async with aiohttp.ClientSession() as session:
                auth = MyStiebelAuth(session, self.username, self.password, self.client_id)
                await auth.authenticate()

                installations = await auth.get_installations()
                first_installation_id = str(installations["items"][0]["id"])

                self.logger.debug(f"First installation Id: {first_installation_id}")

        except Exception as e:
            self.logger.error(f"Fehler bei Authentifizierung oder Abruf: {e}")

        self.alive = False

        self.logger.notice("plugin_coro finished")
        return
