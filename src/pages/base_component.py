"""
Base component class for Component-based POM.

All UI components should inherit from this class to get consistent
locator handling and expect() wrappers.
"""

from playwright.sync_api import Locator, Page, expect


class BaseComponent:
    """
    Base class for all UI components.

    Provides:
    - Consistent locator root
    - Common expect() wrappers
    - Wait strategies

    Usage:
        class HeaderComponent(BaseComponent):
            def __init__(self, page: Page):
                super().__init__(page, \"header\")

            @property
            def logo(self) -> Locator:
                return self.locator(\".logo\")

            def click_logo(self) -> None:
                self.logo.click()
    """

    def __init__(self, page: Page, root_selector: str):
        """
        Initialize component.

        Args:
            page: Playwright page instance
            root_selector: CSS selector for component root element
        """
        self.page = page
        self.root_locator = page.locator(root_selector)

    @property
    def locator(self) -> Locator:
        """Get root locator for this component."""
        return self.root_locator

    def _child(self, selector: str) -> Locator:
        """
        Get child locator relative to component root.

        Args:
            selector: CSS selector relative to root

        Returns:
            Child locator
        """
        return self.root_locator.locator(selector)

    def expect_visible(self, timeout: float | None = None) -> None:
        """Assert component is visible."""
        expect(self.root_locator).to_be_visible(timeout=timeout)

    def expect_hidden(self, timeout: float | None = None) -> None:
        """Assert component is hidden."""
        expect(self.root_locator).to_be_hidden(timeout=timeout)

    def expect_enabled(self, timeout: float | None = None) -> None:
        """Assert component is enabled."""
        expect(self.root_locator).to_be_enabled(timeout=timeout)

    def expect_disabled(self, timeout: float | None = None) -> None:
        """Assert component is disabled."""
        expect(self.root_locator).to_be_disabled(timeout=timeout)

    def expect_has_text(self, text: str, timeout: float | None = None) -> None:
        """Assert component has exact text."""
        expect(self.root_locator).to_have_text(text, timeout=timeout)

    def expect_contains_text(self, text: str, timeout: float | None = None) -> None:
        """Assert component contains text."""
        expect(self.root_locator).to_contain_text(text, timeout=timeout)

    def wait_for_visible(self, timeout: float | None = None) -> None:
        """Wait for component to be visible."""
        self.root_locator.wait_for(state="visible", timeout=timeout)

    def wait_for_hidden(self, timeout: float | None = None) -> None:
        """Wait for component to be hidden."""
        self.root_locator.wait_for(state="hidden", timeout=timeout)
