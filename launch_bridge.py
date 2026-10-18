import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

PROFILE_DIR = "/Users/niuniu/Library/Application Support/gflow-cli/profile_qixian771"
EXTENSION_DIR = "/Users/niuniu/Desktop/flow cli/flowkit_repo/extension"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

async def main():
    print(f"Launching Chrome with profile: {PROFILE_DIR}")
    print(f"Loading extension from: {EXTENSION_DIR}")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            executable_path=CHROME_PATH,
            headless=False,
            args=[
                f"--disable-extensions-except={EXTENSION_DIR}",
                f"--load-extension={EXTENSION_DIR}",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
            ignore_default_args=["--disable-extensions"],
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        print("Navigating to https://flow.google.com/ ...")
        await page.goto("https://flow.google.com/", wait_until="domcontentloaded")
        print("Page loaded. FlowKit extension should now hook into session.")
        
        # Keep alive indefinitely so the background bridge stays connected
        while True:
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
