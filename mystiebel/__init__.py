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
from typing import Any

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
        if self.has_iattr(item.conf, 'mystiebel_control'):
            control_id = item.conf['mystiebel_control']
            self.logger.debug(f"Registered control_id {control_id} for item {item.property.path}")
            return self.update_item

    def parse_logic(self, logic):
        pass

    def update_item(self, item, caller=None, source=None, dest=None):
        if caller == 'MyStiebel':
            return

        if self.has_iattr(item.conf, 'mystiebel_control'):
            control_id = item.conf['mystiebel_control']
            self.logger.debug(f"Item change detected: control_id={control_id}, value={item()} from caller={caller}")
            asyncio.create_task(self.send_control_value(control_id, item()))

    async def send_control_value(self, control_id: int, value: Any):
        try:
            await self.websocketclient.set_value(control_id, value)

        except Exception as e:
            self.logger.error(f"Failed to send control command: {e}")

    def poll_device(self):
        pass

    async def plugin_coro(self):
        selected_installation = self.get_parameter_value('installation')
        await self.initialize_websocketclient(selected_installation)

        self.websocketclient.start()
        self.alive = True

        try:
            while self.alive:
                await asyncio.sleep(60)
                await self.websocketclient.request_values()
        except Exception as e:
            self.logger.error(f"Error occurred in item request: {e}")

        await self.session.close()
        self.alive = False
        return

    def send_item_updates(self, sensor_id: int, value: Any) -> None:
        for item in self.itemlist:
            item_sensor_id = item.conf.get('mystiebel_sensor')
            if sensor_id == item_sensor_id:
                try:
                    current_value = item()
                    if isinstance(item(), float):
                        value = float(value)
                    elif isinstance(item(), int):
                        value = int(float(value))
                    if current_value != value:
                        self.logger.debug(f"Updating item {item.property.path} with value {value} for sensor_id {sensor_id}")
                        item(value, caller='MyStiebel', source='plugin')
                except Exception as e:
                    self.logger.error(f"Failed to update item for sensor {sensor_id}: {e}")

# pyStiebel specific
    async def initialize_websocketclient(self, selected_installation) -> None:
        self.session = aiohttp.ClientSession()
        self.auth = MyStiebelAuth(self.session, self.username, self.password, self.client_id)
        self.installation_id = await self.get_installation(selected_installation, self.auth)
        self.websocketclient = WebSocketClient(self.session, self.auth, self.installation_id, self.client_id, self.sensor_ids, self.send_item_updates)

    async def get_installation(self, selected_installation, auth) -> str:
        installations = await auth.get_installations()
        available_installation_ids = [str(entry['id']) for entry in installations.get('items', [])]
        if not available_installation_ids:
            raise Exception("No installation available at myStiebel.")

        if not selected_installation:
            self.logger.warning(f"No installation configured. Possible candiates are:")
            for entry in installations['items']:
                self.logger.info(f" - {entry['id']}: {entry['name']}")
            self.logger.info(f"Choosing first: {available_installation_ids[0]}")
            return available_installation_ids[0]
        else:
            if selected_installation in available_installation_ids:
                return selected_installation
            else:
                raise Exception(f"Installation '{installation}'no available at myStiebel")
