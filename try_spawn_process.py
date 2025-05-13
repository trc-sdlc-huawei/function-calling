import asyncio
import os

async def spawn_process(command: str, args: list, env: dict):
    """Spawn a process with command/args/env and check success."""
    merged_env = os.environ.copy()
    merged_env.update(env)

    process = await asyncio.create_subprocess_exec(
        command, *args,
        env=merged_env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    print("STDOUT:", stdout.decode().strip())
    print("STDERR:", stderr.decode().strip())

    if process.returncode == 0:
        print("✅ Process succeeded")
    else:
        print(f"❌ Process failed with return code {process.returncode}")

    return process.returncode

if __name__ == "__main__":
    asyncio.run(spawn_process(
        "node",
        ["/home/user1/work/git-repo/quickstart-resources/weather-server-typescript/build/index.js"],
        {}
    ))
