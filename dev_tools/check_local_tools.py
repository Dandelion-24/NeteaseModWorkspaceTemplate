"""MCP initialization and enumeration only; never invokes a game-facing tool."""
import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys

from resource_manager import ROOT, registry, resource_status


async def check(selected):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamablehttp_client

    result = {}
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
               TRACY_BIN_DIR=str(ROOT / 'dev_tools/external/mcdk-mcp-tracy/bin'),
               PYTHONPATH=str(ROOT / 'dev_tools/external/mcdk-mcp-tracy/src') + os.pathsep + os.environ.get('PYTHONPATH', ''))
    if 'tracy' in selected:
        params = StdioServerParameters(command=sys.executable, args=['-B', '-m', 'mcdk_mcp_tracy', '--stdio'], env=env)
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as client:
                await asyncio.wait_for(client.initialize(), timeout=20)
                names = sorted(tool.name for tool in (await asyncio.wait_for(client.list_tools(), timeout=20)).tools)
                if not {'tracy_native_capture', 'tracy_status'}.issubset(names):
                    raise RuntimeError('Tracy did not advertise the expected tools')
                result['tracy'] = {'status': 'PASS', 'tools': names}
    if 'modpc' in selected:
        with socket.socket() as socket_probe:
            socket_probe.bind(('127.0.0.1', 0))
            port = socket_probe.getsockname()[1]
        process = subprocess.Popen([sys.executable, '-B', str(ROOT / 'dev_tools/external/ModPC-MCP-Tool/server.py'),
                                    '--http-host', '127.0.0.1', '--http-port', str(port)],
                                   env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError('ModPC server exited before handshake')
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=0.1):
                        break
                except OSError:
                    await asyncio.sleep(0.2)
            else:
                raise RuntimeError('ModPC server did not listen')
            async with streamablehttp_client('http://127.0.0.1:%d/mcp/' % port) as (reader, writer, _):
                async with ClientSession(reader, writer) as client:
                    await asyncio.wait_for(client.initialize(), timeout=20)
                    names = sorted(tool.name for tool in (await asyncio.wait_for(client.list_tools(), timeout=20)).tools)
                    if names != ['execute_script', 'get_doc']:
                        raise RuntimeError('ModPC did not advertise the expected tools')
                    result['modpc'] = {'status': 'PASS', 'tools': names}
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tools', nargs='+', choices=('tracy', 'modpc'))
    args = parser.parse_args()
    try:
        resources = registry()
        status = {key: resource_status(resources[key]) for key in ('tracy', 'modpc')}
        selected = args.tools or [key for key, row in status.items() if row['status'] == 'READY']
        unavailable = [key for key in selected if status[key]['status'] != 'READY']
        if unavailable or not selected:
            print(json.dumps({'status': 'NOT_READY', 'resources': status, 'game_tools_called': False}, ensure_ascii=False, indent=2))
            return 2
        tested = asyncio.run(check(selected))
        print(json.dumps({'status': 'PASS', 'tested': tested, 'not_tested': [key for key in status if key not in selected],
                          'game_tools_called': False, 'game_tested': False}, ensure_ascii=False, indent=2))
        return 0
    except ImportError as error:
        print(json.dumps({'status': 'NOT_READY', 'reason': str(error), 'next': 'Run dev_tools/setup_python.ps1 with the required options.'}))
        return 2
    except Exception as error:
        print(json.dumps({'status': 'FAIL', 'reason': str(error), 'game_tools_called': False}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
