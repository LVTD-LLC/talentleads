import "../styles/index.css";

import { Application } from "@hotwired/stimulus";
import { definitionsFromContext } from "@hotwired/stimulus-webpack-helpers";
import Dropdown from 'stimulus-dropdown';
import Reveal from 'stimulus-reveal-controller';

const MODAL_FOCUS_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

class AccessibleDropdown extends Dropdown {
  static targets = ['menu', 'button'];

  connect() {
    this.handleModalKeydown = this.handleModalKeydown.bind(this);
    super.connect();
    this.updateExpanded();
  }

  disconnect() {
    this.deactivateModal();

    if (super.disconnect) {
      super.disconnect();
    }
  }

  toggle(event) {
    super.toggle(event);
    requestAnimationFrame(() => this.updateExpanded());
  }

  hide(event) {
    const closeEvent = event || { target: document.documentElement };
    super.hide(closeEvent);
    requestAnimationFrame(() => this.updateExpanded());
  }

  updateExpanded() {
    if (!this.hasButtonTarget || !this.hasMenuTarget) {
      return;
    }

    const expanded = !this.menuTarget.classList.contains('hidden');
    this.buttonTargets.forEach((button) => {
      button.setAttribute('aria-expanded', String(expanded));
    });
    this.menuTarget.setAttribute('aria-hidden', String(!expanded));

    if (expanded && this.isModalMenu()) {
      this.activateModal();
    } else {
      this.deactivateModal();
    }
  }

  isModalMenu() {
    return this.menuTarget.getAttribute('role') === 'dialog'
      && this.menuTarget.getAttribute('aria-modal') === 'true';
  }

  activateModal() {
    if (this.modalActive) {
      return;
    }

    this.modalActive = true;
    this.lastFocusedElement = document.activeElement;
    document.documentElement.classList.add('tl-modal-open');
    document.addEventListener('keydown', this.handleModalKeydown);

    const initialFocus = this.menuTarget.querySelector('[data-dropdown-initial-focus]')
      || this.getFocusableElements()[0]
      || this.menuTarget;

    requestAnimationFrame(() => {
      initialFocus.focus({ preventScroll: true });
    });
  }

  deactivateModal() {
    if (!this.modalActive) {
      return;
    }

    this.modalActive = false;
    document.documentElement.classList.remove('tl-modal-open');
    document.removeEventListener('keydown', this.handleModalKeydown);

    if (this.lastFocusedElement && document.contains(this.lastFocusedElement)) {
      this.lastFocusedElement.focus({ preventScroll: true });
    }

    this.lastFocusedElement = null;
  }

  getFocusableElements() {
    return Array.from(this.menuTarget.querySelectorAll(MODAL_FOCUS_SELECTOR))
      .filter((element) => element.getClientRects().length > 0);
  }

  handleModalKeydown(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      this.hide();
      return;
    }

    if (event.key !== 'Tab') {
      return;
    }

    const focusableElements = this.getFocusableElements();

    if (focusableElements.length === 0) {
      event.preventDefault();
      this.menuTarget.focus({ preventScroll: true });
      return;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    if (event.shiftKey && document.activeElement === firstElement) {
      event.preventDefault();
      lastElement.focus({ preventScroll: true });
    } else if (!event.shiftKey && document.activeElement === lastElement) {
      event.preventDefault();
      firstElement.focus({ preventScroll: true });
    }
  }
}

// Stimulus
const application = Application.start();
const context = require.context("../controllers", true, /\.js$/);
application.load(definitionsFromContext(context));

application.register('dropdown', AccessibleDropdown);
application.register('reveal', Reveal);
