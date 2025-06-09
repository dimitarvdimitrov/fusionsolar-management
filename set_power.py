from playwright.sync_api import sync_playwright
import time
import logging
import sys
import os
import datetime
import tempfile
from config import TIMEZONE
from storage_interface import StorageInterface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Default directory for storing screenshots is now imported from config.py

class Screenshotter:

    def __init__(self, page, storage: StorageInterface):
        """
        Initialize the Screenshotter with a Playwright page and session path.

        Args:
            page: Playwright page object
            storage (StorageInterface): Storage interface to use for saving screenshots
        """
        self.page = page
        self.session_path = f"screenshots/session_{datetime.datetime.now(TIMEZONE).strftime('%Y-%m-%d_%H-%M')}"
        self.storage = storage
        logger.info("Screenshotter initialized")

    def take_screenshot(self, action_name):
        """
        Take a screenshot of the current page state and save it using the storage interface.
        If no storage is provided, it will save to the local filesystem.

        Args:
            action_name (str): Name of the action being performed

        Returns:
            str: Path to the saved screenshot
        """
        try:
            time.sleep(1)  # Delay to ensure the page is fully loaded
            # Create timestamp for the filename
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            # Create a filename with timestamp and action name
            filename = f"{timestamp}_{action_name}.png"
            filepath = os.path.join(self.session_path, filename)

            # Use a temporary file for the screenshot, then upload to storage
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_path = tmp_file.name

            # Take the screenshot to the temp file
            self.page.screenshot(path=tmp_path, full_page=True)

            # Read the screenshot data
            with open(tmp_path, 'rb') as f:
                screenshot_data = f.read()

            # Upload to storage
            success = self.storage.write_binary(filepath, screenshot_data)

            # Remove the temporary file
            os.unlink(tmp_path)

            if success:
                logger.info(f"Screenshot saved to storage: {filepath}")
            else:
                logger.error(f"Failed to save screenshot to storage: {filepath}")
        except Exception as e:
            logger.error(f"Failed to take screenshot for '{action_name}': {e}")

class SetPower:
    """
    Class to handle power limit setting for Huawei FusionSolar SmartLogger device.
    """
    
    def __init__(self, username, password, storage):
        """
        Initialize the SetPower class with login credentials.
        
        Args:
            username (str): FusionSolar username
            password (str): FusionSolar password
            storage (StorageInterface): Storage interface for saving screenshots
        """
        self.username = username
        self.password = password
        self.storage = storage
        logger.info("SetPower instance initialized")
    
    def set_power_limit(self, power_limit: str) -> bool:
        """
        Login to Huawei FusionSolar and set the power limit for a SmartLogger device.
        
        Args:
            power_limit (str): Power limit value to set (in kW); use "no limit" for no limit

        Returns:
            bool: True if operation succeeded, False otherwise
        """
        logger.info("Starting set_power_limit function")
        

        with sync_playwright() as playwright:
            logger.info("Initializing Playwright")
            logger.info("Launching browser")
            browser = playwright.chromium.launch(slow_mo=200, args=["--disable-gpu", "--single-process"])
            logger.info("Browser launched successfully")

            try:
                # Create a new page
                logger.info("Creating new page")
                page = browser.new_page()
                logger.info("New page created")

                # Set up a session directory for screenshots
                screenshotter = Screenshotter(page, self.storage)

                # Navigate to the login page
                logger.info("Navigating to login page")
                page.goto('https://eu5.fusionsolar.huawei.com/unisso/login.action')
                screenshotter.take_screenshot("login_page_loaded")
                logger.info("Login page loaded")
                
                # Fill in the username and password fields
                logger.info("Filling username and password")
                page.fill('input#username', self.username)
                page.fill('input#value', self.password)
                screenshotter.take_screenshot("credentials_filled")
                logger.info("Username and password filled")

                
                # Click the login button
                logger.info("Clicking login button")
                page.click('span#submitDataverify')
                screenshotter.take_screenshot("login_button_clicked")
                logger.info("Login button clicked")
                
                # Wait for navigation to complete after login
                logger.info("Waiting for navigation to complete")
                page.wait_for_load_state('networkidle')
                screenshotter.take_screenshot("login_completed")
                logger.info("Navigation completed")
                
                # Navigate to Device Management
                logger.info("Clicking on Device Management tab")
                page.click('span.monitor-tab a:has-text("Device Management")')
                screenshotter.take_screenshot("device_management_clicked")
                logger.info("Device Management tab clicked")
                
                # Find the SmartLogger row and select it
                logger.info("Finding and selecting SmartLogger row")
                page.locator('tr').filter(has_text='SmartLogger').locator('input.ant-checkbox-input').click()
                screenshotter.take_screenshot("smartlogger_selected")
                logger.info("SmartLogger row selected")
                
                # Open Set Parameters dialog
                logger.info("Clicking Set Parameters button")
                page.click('button:has-text("Set Parameters")')
                screenshotter.take_screenshot("set_parameters_clicked")
                logger.info("Set Parameters button clicked")
                
                # Navigate to Active Power Control tab
                logger.info("Clicking Active Power Control tab")
                page.click('div#rc-tabs-0-tab-Active\\ Power\\ Control')
                screenshotter.take_screenshot("active_power_control_tab")
                logger.info("Active Power Control tab clicked")

                if power_limit == "no limit":
                    if page.is_visible('span[title="Limited Power Grid (kW)"]'):
                        page.click('span[title="Limited Power Grid (kW)"]')
                        screenshotter.take_screenshot("limited_power_grid_clicked")

                        # Select No limit
                        logger.info("Selecting No limit")
                        page.click('div[title="No limit"]')
                        screenshotter.take_screenshot("no_limit_clicked")
                        logger.info("No limit field clicked")
                    elif page.is_visible('span[title="Remote communication scheduling"]'):
                        page.click('span[title="Remote communication scheduling"]')
                        screenshotter.take_screenshot("remote_communication_scheduling_clicked")

                        # Select No limit
                        logger.info("Selecting No limit")
                        page.click('div[title="No limit"]')
                        screenshotter.take_screenshot("no_limit_clicked")
                        logger.info("No limit field clicked")

                    elif page.is_visible('span[title="No limit"]'):
                        logger.info("Power limit is set to 'No limit' already")
                        return False
                    screenshotter.take_screenshot("select_active_power_control_mode")
                else:
                    # Check if Limited Power Grid field is already selected
                    logger.info("Checking if Limited Power Grid field is already selected")
                    if page.is_visible('span[title="Limited Power Grid (kW)"]'):
                        logger.info("Limited Power Grid field is already selected")
                    else:
                        logger.info("Limited Power Grid field is not selected")
                        screenshotter.take_screenshot("limited_power_grid_not_selected")
                        if page.is_visible('span[title="Remote communication scheduling"]'):
                            # Select Remote communication scheduling
                            logger.info("Selecting Remote communication scheduling")
                            page.click('span[title="Remote communication scheduling"]')
                            screenshotter.take_screenshot("remote_comm_scheduling_selected")
                            logger.info("Remote communication scheduling selected")
                        elif page.is_visible('span[title="No limit"]'):
                            # Select No limit
                            logger.info("Selecting No limit")
                            page.click('span[title="No limit"]')
                            screenshotter.take_screenshot("no_limit_clicked")
                            logger.info("No limit field clicked")
                        else:
                            raise Exception("Neither Limited Power Grid nor Remote communication scheduling is available; can't select 'Limited Power Grid (kW)'")

                        # Select Limited Power Grid field
                        logger.info("Selecting Limited Power Grid field")
                        page.click('div[title="Limited Power Grid (kW)"]')
                        screenshotter.take_screenshot("limited_power_grid_clicked")
                        logger.info("Limited Power Grid field clicked")

                    # Set start active control
                    logger.info("Setting Start control field")
                    page.locator('div#signal-config-form-item-230200032').locator('input').fill('Yes')
                    page.locator('div#signal-config-form-item-230200032').locator('input').press('Enter')
                    screenshotter.take_screenshot("set_start_control_input")
                    logger.info("Start control field set")

                    # Hover over input so it's scrolled into view
                    logger.info("Hovering over power limit input field")
                    page.locator('div#signal-config-form-item-21098').locator('input').hover()
                    screenshotter.take_screenshot("hover_power_limit_input")
                    logger.info("Hovered over power limit input field")

                    # Set the power limit value
                    logger.info(f"Setting power limit to: {power_limit} kW")
                    page.locator('div#signal-config-form-item-21098').locator('input').fill(power_limit)
                    screenshotter.take_screenshot(f"power_limit_set_{power_limit}")
                    logger.info("Power limit value set")
                
                # Save the changes
                if page.locator('button:has-text("Save")').is_enabled():
                    logger.info("Clicking Save button")
                    page.click('button:has-text("Save")')
                    screenshotter.take_screenshot("save_button_clicked")
                    logger.info("Save button clicked")
                else:
                    logger.info("Save button is not enabled, skipping click")
                    screenshotter.take_screenshot("save_button_not_enabled")
                    return False
                
                # Wait for success message
                logger.info("Waiting for success message")
                success = False
                timeout = 120
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    if page.locator('div.ant-modal-confirm-content').filter(has_text='Operation succeeded.').is_visible():
                        success = True
                        screenshotter.take_screenshot("operation_succeeded")
                        logger.info("Operation succeeded!")
                        break
                    # Take a screenshot every 10 seconds while waiting
                    if int(time.time() - start_time) % 10 == 0:
                        screenshotter.take_screenshot(f"waiting_for_confirmation_{int(time.time() - start_time)}s")
                    time.sleep(1)
                    logger.info("Waiting for confirmation...")
                
                if not success:
                    screenshotter.take_screenshot("operation_timeout_or_failed")
                    logger.warning("Operation timed out or failed")

                logger.info(f"Returning success status: {success}")
                return success
                
            except Exception as e:
                logger.error(f"An error occurred: {e}")
                # Take screenshot of the error state if possible
                try:
                    screenshotter.take_screenshot("error_state")
                except:
                    pass
                raise e
            finally:

                # Save final state screenshot
                screenshotter.take_screenshot("final_state")

                # Close the browser
                logger.info("Closing browser")
                browser.close()
                logger.info("Browser closed")
