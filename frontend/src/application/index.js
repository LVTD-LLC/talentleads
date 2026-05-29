import "../styles/index.css";

import { Application } from "@hotwired/stimulus";
import { definitionsFromContext } from "@hotwired/stimulus-webpack-helpers";
import Dropdown from 'stimulus-dropdown';
import Reveal from 'stimulus-reveal-controller';

class AccessibleDropdown extends Dropdown {
  static targets = ['menu', 'button'];

  connect() {
    super.connect();
    this.updateExpanded();
  }

  toggle(event) {
    super.toggle(event);
    requestAnimationFrame(() => this.updateExpanded());
  }

  hide(event) {
    super.hide(event);
    requestAnimationFrame(() => this.updateExpanded());
  }

  updateExpanded() {
    if (!this.hasButtonTarget) {
      return;
    }

    const expanded = !this.menuTarget.classList.contains('hidden');
    this.buttonTargets.forEach((button) => {
      button.setAttribute('aria-expanded', String(expanded));
    });
  }
}

// Stimulus
const application = Application.start();
const context = require.context("../controllers", true, /\.js$/);
application.load(definitionsFromContext(context));

application.register('dropdown', AccessibleDropdown);
application.register('reveal', Reveal);
