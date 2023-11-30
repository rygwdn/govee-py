#!/usr/bin/env python

from govee_led_wez import GoveeController
from govee_led_wez.http import http_get_ttr, http_get_ttr_token
from pprint import pprint
import asyncio

api_key = ""
user = ""
password = ""

async def main():
    controller = GoveeController()
    controller.set_http_api_key(api_key)
    await controller.query_http_devices()

    #controller.start_http_poller()
    controller.start_lan_poller()
    await asyncio.sleep(100)

    ttr = await controller.query_scenes(user, password)
    pprint(ttr)

    #pprint(controller.devices)

    #state = await controller.update_device_state(controller.devices["31:12:C3:35:33:33:5C:42"])
    #pprint(state)

    await controller.set_scene(ttr[1]["device"], ttr[1]["iotCommand"])

asyncio.run(main())
