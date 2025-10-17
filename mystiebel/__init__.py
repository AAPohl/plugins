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


# If a needed package is imported, which might be not installed in the Python environment,
# add it to a requirements.txt file within the plugin's directory


class myStiebel(SmartPlugin):
    """
    Main class of the Plugin. Does all plugin specific stuff and provides
    the update functions for the items

    HINT: Please have a look at the SmartPlugin class to see which
    class properties and methods (class variables and class functions)
    are already available!
    """

    PLUGIN_VERSION = '1.0.0'    # (must match the version specified in plugin.yaml), use '1.0.0' for your initial plugin Release

    def __init__(self, sh):
        super().__init__()

        self.username = self.get_parameter_value('username')
        self.password = self.get_parameter_value('password')

        # Some Id: Fix, but different for each instance
        self.client_id = "3f2504e0-4f89-41d3-9a0c-0405e82c3301"
        self.logger.debug(f"Client_Id: {self.client_id}")

        self.init_webinterface(WebInterface)

        return

    def run(self):
        self.logger.debug("myStiebel Plugin started")
        self.start_asyncio(self.plugin_coro())

    async def plugin_coro(self):
        self.logger.debug("enter async")
        self.alive = True
        
        await asyncio.sleep(5)
        self.logger.debug("leave async")
        self.alive = False

    def stop(self):
        """
        Stop method for the plugin
        """
        self.logger.dbghigh(self.translate("Methode '{method}' aufgerufen", {'method': 'stop()'}))
        self.alive = False     # if using asyncio, do not set self.alive here. Set it in the session coroutine

        # let the plugin change the state of pause_item
        if self._pause_item:
            self._pause_item(True, self.get_fullname())

        # this stops all schedulers the plugin has started.
        # you can disable/delete the line if you don't use schedulers
        self.scheduler_remove_all()

        # stop the asyncio eventloop and it's thread
        # If you use asyncio, enable the following line
        self.stop_asyncio()

        # If you called connect() on run(), disconnect here
        # (remember to write a disconnect() method!)
        #self.disconnect()

        # also, clean up anything you set up in run(), so the plugin can be
        # cleanly stopped and started again

    def parse_item(self, item):
        """
        Default plugin parse_item method. Is called when the plugin is initialized.
        The plugin can, corresponding to its attribute keywords, decide what to do with
        the item in future, like adding it to an internal array for future reference
        :param item:    The item to process.
        :return:        If the plugin needs to be informed of an items change you should return a call back function
                        like the function update_item down below. An example when this is needed is the knx plugin
                        where parse_item returns the update_item function when the attribute knx_send is found.
                        This means that when the items value is about to be updated, the call back function is called
                        with the item, caller, source and dest as arguments and in case of the knx plugin the value
                        can be sent to the knx with a knx write function within the knx plugin.
        """
        # check for pause item
        if item.property.path == self._pause_item_path:
            self.logger.debug(f'pause item {item.property.path} registered')
            self._pause_item = item
            self.add_item(item, updating=True)
            return self.update_item

        if self.has_iattr(item.conf, 'foo_itemtag'):
            self.logger.debug(f"parse item: {item}")

        # todo
        # if interesting item for sending values:
        #   self._itemlist.append(item)
        #   return self.update_item

    def parse_logic(self, logic):
        """
        Default plugin parse_logic method
        """
        if 'xxx' in logic.conf:
            # self.function(logic['name'])
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
        """
        Polls for updates of the device

        This method is only needed, if the device (hardware/interface) does not propagate
        changes on it's own, but has to be polled to get the actual status.
        It is called by the scheduler which is set within run() method.
        """
        # # get the value from the device
        # device_value = ...
        #
        # # find the item(s) to update:
        # for item in self.sh.find_items('...'):
        #
        #     # update the item by calling item(value, caller, source=None, dest=None)
        #     # - value and caller must be specified, source and dest are optional
        #     #
        #     # The simple case:
        #     item(device_value, self.get_fullname())
        #     # if the plugin is a gateway plugin which may receive updates from several external sources,
        #     # the source should be included when updating the value:
        #     item(device_value, self.get_fullname(), source=device_source_id)
        pass

    async def plugin_coro(self):
        """
        Coroutine for the plugin session (only needed, if using asyncio)

        This coroutine is run as the PluginTask and should
        only terminate, when the plugin is stopped
        """
        self.logger.notice("plugin_coro started")

        self.alive = True

        # ...

        self.alive = False

        self.logger.notice("plugin_coro finished")
        return
