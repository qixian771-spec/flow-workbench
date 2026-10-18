import asyncio
from playwright.async_api import async_playwright

PROFILE_DIR = "/Users/niuniu/Library/Application Support/gflow-cli/profile_qixian771"
EXTENSION_DIR = "/Users/niuniu/Desktop/flow cli/flowkit_repo/extension"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            executable_path=CHROME_PATH,
            headless=False,
            args=[
                f"--disable-extensions-except={EXTENSION_DIR}",
                f"--load-extension={EXTENSION_DIR}",
            ],
            ignore_default_args=["--disable-extensions"],
        )
        print("Service workers count:", len(context.service_workers))
        for sw in context.service_workers:
            print("SW url:", sw.url)
        
        # Wait a bit to see if SW registers
        if not context.service_workers:
            sw = await context.wait_for_event("serviceworker", timeout=5000)
            print("Detected SW:", sw.url)
        
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
