import os
import shutil

from . import exceptions
from pytest_selenium_pdiff import settings
from .utils import ensure_path_exists


def screenshot_matches(driver, screenshot_name):
    __tracebackhide__ = True  # noqa

    storage_path = settings['SCREENSHOTS_PATH']
    artifacts_path = settings['PDIFF_PATH']

    expected_screenshot = os.path.join(storage_path, screenshot_name + '.png')
    pdiff_comparison = os.path.join(artifacts_path, screenshot_name + '.diff.png')
    captured_screenshot = os.path.join(artifacts_path, screenshot_name + '.captured.png')

    ensure_path_exists(os.path.dirname(expected_screenshot))
    ensure_path_exists(os.path.dirname(pdiff_comparison))

    have_stored_screenshot = os.path.exists(expected_screenshot)

    if not have_stored_screenshot and not settings['ALLOW_SCREENSHOT_CAPTURE']:
        raise exceptions.MissingScreenshot(screenshot_name, expected_screenshot)

    driver.get_screenshot_as_file(captured_screenshot)

    if have_stored_screenshot:
        if settings['USE_IMAGEMAGICK']:
            matches_expected = use_imagemagick_compare(captured_screenshot, expected_screenshot, pdiff_comparison)
        elif settings['USE_PERCEPTUALDIFF']:
            matches_expected = use_perceptualdiff(captured_screenshot, expected_screenshot, pdiff_comparison)

        if not matches_expected:
            if os.path.exists(pdiff_comparison):
                raise exceptions.ScreenshotMismatchWithDiff(screenshot_name, expected_screenshot, captured_screenshot,
                                                            pdiff_comparison)
            else:
                raise exceptions.ScreenshotMismatch(screenshot_name, expected_screenshot, captured_screenshot)
    elif settings['ALLOW_SCREENSHOT_CAPTURE']:
        shutil.move(captured_screenshot, expected_screenshot)

    return True


def use_imagemagick_compare(captured_screenshot, expected_screenshot, pdiff_comparison):
    from sh import compare

    # Arguments list: http://www.imagemagick.org/script/compare.php
    result = compare(
        expected_screenshot,
        captured_screenshot,
        '-metric', 'AE',
        '-highlight-color', 'blue',
        '-compose', 'src-over',
        pdiff_comparison,
        _ok_code=[0, 1, 2]
    )

    if result.exit_code == 2:
        return False

    pixel_errors = int(result.stderr)

    return pixel_errors == 0


def use_perceptualdiff(captured_screenshot, expected_screenshot, pdiff_comparison):
    from sh import perceptualdiff

    result = perceptualdiff(
        '-output', pdiff_comparison,
        expected_screenshot,
        captured_screenshot,
        _ok_code=[0, 1]
    )

    return result.exit_code == 0
