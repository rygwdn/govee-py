from dataclasses import dataclass
import logging
import ssl
import time
import json
from typing import Any, Dict, List

import aiohttp
import certifi

_LOGGER = logging.getLogger(__name__)


@dataclass
class GoveeHttpDeviceDefinition:
    """Device information, available via HTTP API"""

    device_id: str
    model: str
    device_name: str
    controllable: bool
    retrievable: bool
    supported_commands: List[str]
    properties: Dict[str, Any]


async def _extract_failure_message(response) -> str:
    try:
        data = await response.json()
        if "message" in data:
            return data["message"]
    except Exception:  # pylint: disable=broad-except
        pass
    return await response.text()


async def http_get_devices(api_key: str) -> List[GoveeHttpDeviceDefinition]:
    """Requests the list of devices via the HTTP API"""
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    conn = aiohttp.TCPConnector(ssl=ssl_context)
    message = "Failed for an unknown reason"
    async with aiohttp.ClientSession(connector=conn) as session:
        async with session.get(
            url="https://developer-api.govee.com/v1/devices",
            headers={"Govee-API-Key": api_key},
        ) as response:
            if response.status == 200:
                data = await response.json()
                if (
                    ("data" in data)
                    and ("devices" in data["data"])
                    and isinstance(data["data"]["devices"], list)
                ):
                    return [
                        GoveeHttpDeviceDefinition(
                            device_id=d["device"],
                            model=d["model"],
                            device_name=d["deviceName"],
                            controllable=d["controllable"],
                            retrievable=d["retrievable"],
                            supported_commands=d["supportCmds"],
                            properties=d.get("properties", {}),
                        )
                        for d in data["data"]["devices"]
                    ]

            message = await _extract_failure_message(response)
    raise RuntimeError(f"failed to get devices: {message}")


async def http_get_state(api_key: str, device_id: str, model: str) -> List[Any]:
    """Requests a list of properties representing the state of the specified device"""
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    conn = aiohttp.TCPConnector(ssl=ssl_context)
    message = "Failed for an unknown reason"
    async with aiohttp.ClientSession(connector=conn) as session:
        async with session.get(
            url="https://developer-api.govee.com/v1/devices/state",
            headers={"Govee-API-Key": api_key},
            params={"model": model, "device": device_id},
        ) as response:
            if response.status == 200:
                data = await response.json()
                if "data" in data and "properties" in data["data"]:
                    return data["data"]["properties"]

            message = await _extract_failure_message(response)
    raise RuntimeError(f"failed to get device state: {message}")


async def http_device_control(api_key: str, params: Dict[str, Any]):
    """Sends a control request"""
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    conn = aiohttp.TCPConnector(ssl=ssl_context)
    message = "Failed for an unknown reason"
    import pprint; pprint.pprint(params)
    async with aiohttp.ClientSession(connector=conn) as session:
        async with session.put(
            url="https://developer-api.govee.com/v1/devices/control",
            headers={"Govee-API-Key": api_key},
            json=params,
        ) as response:
            _LOGGER.debug("http control request %s -> %s", params, response)
            if response.status == 200:
                resp = await response.json()
                return resp
            message = await _extract_failure_message(response)
    raise RuntimeError(f"failed to control device: {message}")

async def http_get_ttr_token(username: str, password: str):
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    conn = aiohttp.TCPConnector(ssl=ssl_context)
    message = "Failed for an unknown reason"

    async with aiohttp.ClientSession(connector=conn) as session:
        async with session.post(
            url="https://community-api.govee.com/os/v1/login",
            json={
                "email": username,
                "password": password,
            },
        ) as response:
            #_LOGGER.info("http control request %s -> %s", params, response)
            if response.status == 200:
                resp = await response.json()
                if resp["status"] == 200:
                    return resp["data"]["token"]
            message = await _extract_failure_message(response)
    raise RuntimeError(f"failed to login: {message}")

async def http_get_ttr(ttr_token: str):
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    conn = aiohttp.TCPConnector(ssl=ssl_context)
    message = "Failed for an unknown reason"
    
    async with aiohttp.ClientSession(connector=conn) as session:
        async with session.get(
            url="https://app2.govee.com/bff-app/v1/exec-plat/home",
            headers={
                "Authorization": f"Bearer {ttr_token}",
                "clientType": str(1),
                "iotVersion": str(0),
                "timestamp": str(round(time.time() * 1000)),
                # These may need to change from time to time
                "clientId": "home-assistant",
                "appVersion": "5.6.01",
                "User-Agent": "GoveeHome/5.6.01 (com.ihoment.GoVeeSensor; build:2; iOS 16.5.0) Alamofire/5.6.4",
            }
        ) as response:
            if response.status == 200:
                resp = await response.json()
                if resp["status"] == 200:
                    rules = [
                        {
                            "iotMessage": json.loads(rule["iotMsg"]) if "iotMsg" in rule else None,
                            "device": iotRule["deviceObj"]["device"],
                            "oneClickName": one_click["name"],
                        }
                        for scene in resp["data"]["components"]
                        if "oneClicks" in scene
                        for one_click in scene["oneClicks"]
                        if "iotRules" in one_click
                        for iotRule in one_click["iotRules"]
                        if "rule" in iotRule
                        for rule in iotRule["rule"]
                    ]

                    iotCommands = [
                        {
                            "device": rule["device"],
                            "oneClickName": rule["oneClickName"],
                            "iotCommand": rule["iotMessage"]["msg"]["data"]["command"] if "msg" in rule["iotMessage"] and rule["iotMessage"]["msg"]["cmd"] == "ptReal" else None,
                        }
                        for rule in rules
                    ]

                    return [
                        command for command in iotCommands
                        if command["iotCommand"]
                    ]
            message = await _extract_failure_message(response)
    raise RuntimeError(f"failed to fetch tap to runs: {message}")


    #     // Build and send the request
    # const res = await axios({
    #   url: '',
    #   method: 'get',
    #   headers: {
    #     Authorization: `Bearer ${this.tokenTTR}`,
    #     appVersion: this.appVersion,
    #     clientId: this.clientId,
    #     clientType: 1,
    #     iotVersion: 0,
    #     timestamp: Date.now(),
    #     'User-Agent': this.userAgent,
    #   },
    #   timeout: 10000,
    # });

    # // Check to see we got a response
    # if (!res?.data?.data?.components) {
    #   throw new Error('not a valid response');
    # }

    # return res.data.data.components;


    # Login and get normal token..
    # // Create a client id generated from Govee username which should remain constant
    # let clientSuffix = platform.api.hap.uuid.generate(this.username).replace(/-/g, ''); // 32 chars
    # clientSuffix = clientSuffix.substring(0, clientSuffix.length - 2); // 30 chars
    # this.clientId = `hb${clientSuffix}`; // 32 chars
    # clientId = "ha-test-client"
    async with aiohttp.ClientSession(connector=conn) as session:
        async with session.post(
            url="https://app2.govee.com/account/rest/account/v1/login",
            json={
                "email": username,
                "password": password,
                "client": clientId,
            },
        ) as response:
            #_LOGGER.info("http control request %s -> %s", params, response)
            if response.status == 200:
                resp = await response.json()
                if resp["status"] == 200:
                    return resp
            message = await _extract_failure_message(response)
    raise RuntimeError(f"failed to login: {message}")