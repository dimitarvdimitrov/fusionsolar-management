from playwright.sync_api import sync_playwright
import time
import logging
import sys
import os
import datetime
import pytz
from config import SCREENSHOT_DIR

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

def take_screenshot(page, action_name, session_dir):
    """
    Take a screenshot of the current page state and save it to disk.
    
    Args:
        page: Playwright page object
        action_name (str): Name of the action being performed
        session_dir (str): Directory for the current session
    
    Returns:
        str: Path to the saved screenshot
    """
    try:
        time.sleep(1)  # Delay to ensure the page is fully loaded
        # Create timestamp for the filename
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Create a filename with timestamp and action name
        filename = f"{timestamp}_{action_name}.png"
        filepath = os.path.join(session_dir, filename)
        
        # Take the screenshot
        page.screenshot(path=filepath, full_page=True)
        logger.info(f"Screenshot saved: {filepath}")
        
        return filepath
    except Exception as e:
        logger.error(f"Failed to take screenshot for '{action_name}': {e}")
        return None

def setup_session_directory():
    """
    Set up a unique directory for the current session's screenshots.
    
    Returns:
        str: Path to the session directory
    """
    # Create base directory if it doesn't exist
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)
        logger.info(f"Created screenshot base directory: {SCREENSHOT_DIR}")
    
    # Create a session-specific directory with timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_dir = os.path.join(SCREENSHOT_DIR, f"session_{timestamp}")
    
    os.makedirs(session_dir)
    logger.info(f"Created session directory for screenshots: {session_dir}")
    
    return session_dir

def set_power_limit(username, password, power_limit):
    """
    Login to Huawei FusionSolar and set the power limit for a SmartLogger device.
    
    Args:
        username (str): FusionSolar username
        password (str): FusionSolar password
        power_limit (str): Power limit value to set (in kW)

    Returns:
        bool: True if operation succeeded, False otherwise
    """
    logger.info("Starting set_power_limit function")
    
    # Set up a session directory for screenshots
    session_dir = setup_session_directory()
    
    with sync_playwright() as playwright:
        logger.info("Initializing Playwright")
        # Launch the browser with headless=False to see the browser window
        logger.info("Launching browser")
        browser = playwright.chromium.launch(slow_mo=200)
        logger.info("Browser launched successfully")
        
        try:
            # Create a new page
            logger.info("Creating new page")
            page = browser.new_page()
            logger.info("New page created")
            
            # Navigate to the login page
            logger.info("Navigating to login page")
            page.goto('https://eu5.fusionsolar.huawei.com/unisso/login.action')
            take_screenshot(page, "login_page_loaded", session_dir)
            logger.info("Login page loaded")
            
            # Fill in the username and password fields
            logger.info("Filling username and password")
            page.fill('input#username', username)
            page.fill('input#value', password)
            take_screenshot(page, "credentials_filled", session_dir)
            logger.info("Username and password filled")

            
            # Click the login button
            logger.info("Clicking login button")
            page.click('span#submitDataverify')
            take_screenshot(page, "login_button_clicked", session_dir)
            logger.info("Login button clicked")
            
            # Wait for navigation to complete after login
            logger.info("Waiting for navigation to complete")
            page.wait_for_load_state('networkidle')
            take_screenshot(page, "login_completed", session_dir)
            logger.info("Navigation completed")
            
            # Navigate to Device Management
            logger.info("Clicking on Device Management tab")
            page.click('span.monitor-tab a:has-text("Device Management")')
            take_screenshot(page, "device_management_clicked", session_dir)
            logger.info("Device Management tab clicked")
            
            # Find the SmartLogger row and select it
            logger.info("Finding and selecting SmartLogger row")
            page.locator('tr').filter(has_text='SmartLogger').locator('input.ant-checkbox-input').click()
            take_screenshot(page, "smartlogger_selected", session_dir)
            logger.info("SmartLogger row selected")
            
            # Open Set Parameters dialog
            logger.info("Clicking Set Parameters button")
            page.click('button:has-text("Set Parameters")')
            take_screenshot(page, "set_parameters_clicked", session_dir)
            logger.info("Set Parameters button clicked")
            
            # Navigate to Active Power Control tab
            logger.info("Clicking Active Power Control tab")
            page.click('div#rc-tabs-0-tab-Active\\ Power\\ Control')
            take_screenshot(page, "active_power_control_tab", session_dir)
            logger.info("Active Power Control tab clicked")
            
            # Select Remote communication scheduling
            logger.info("Selecting Remote communication scheduling")
            page.click('span[title="Remote communication scheduling"]')
            take_screenshot(page, "remote_comm_scheduling_selected", session_dir)
            logger.info("Remote communication scheduling selected")
            
            # Select Limited Power Grid field
            logger.info("Clicking Limited Power Grid field")
            page.click('div[title="Limited Power Grid (kW)"]')
            take_screenshot(page, "limited_power_grid_clicked", session_dir)
            logger.info("Limited Power Grid field clicked")
            
            # Set the power limit value
            logger.info(f"Setting power limit to: {power_limit} kW")
            page.locator('div#signal-config-form-item-21098').locator('input').fill(power_limit)
            take_screenshot(page, f"power_limit_set_{power_limit}", session_dir)
            logger.info("Power limit value set")
            
            # Save the changes
            logger.info("Clicking Save button")
            page.click('button:has-text("Save")')
            take_screenshot(page, "save_button_clicked", session_dir)
            logger.info("Save button clicked")
            
            # Wait for success message
            logger.info("Waiting for success message")
            success = False
            timeout = 120
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if page.locator('div.ant-modal-confirm-content').filter(has_text='Operation succeeded.').is_visible():
                    success = True
                    take_screenshot(page, "operation_succeeded", session_dir)
                    logger.info("Operation succeeded!")
                    break
                # Take a screenshot every 10 seconds while waiting
                if int(time.time() - start_time) % 10 == 0:
                    take_screenshot(page, f"waiting_for_confirmation_{int(time.time() - start_time)}s", session_dir)
                time.sleep(1)
                logger.info("Waiting for confirmation...")
            
            if not success:
                take_screenshot(page, "operation_timeout_or_failed", session_dir)
                logger.warning("Operation timed out or failed")
            
            # Save final state screenshot
            take_screenshot(page, "final_state", session_dir)
            
            # Create a summary file with operation details
            summary_path = os.path.join(session_dir, "session_summary.txt")
            with open(summary_path, 'w') as summary_file:
                summary_file.write(f"Session timestamp: {datetime.datetime.now()}\n")
                summary_file.write(f"Power limit set to: {power_limit} kW\n")
                summary_file.write(f"Operation success: {success}\n")
                summary_file.write(f"Total screenshots: {len([f for f in os.listdir(session_dir) if f.endswith('.png')])}\n")
            
            logger.info(f"Session summary saved to: {summary_path}")
            logger.info(f"Returning success status: {success}")
            return success
            
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            # Take screenshot of the error state if possible
            try:
                take_screenshot(page, "error_state", session_dir)
            except:
                pass
            return False
        finally:
            # Close the browser
            logger.info("Closing browser")
            browser.close()
            logger.info("Browser closed")
