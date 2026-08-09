import { Controller } from '@hotwired/stimulus';

export default class extends Controller {
  static targets = ['button', 'dialog', 'input'];

  static values = {
    authenticated: Boolean,
  };

  connect() {
    if (!this.authenticatedValue || !this.hasInputTarget) {
      return;
    }

    const pendingJobUrl = this.pendingJobUrl();
    if (!pendingJobUrl) {
      return;
    }

    this.inputTarget.value = pendingJobUrl;
    this.clearPendingJobUrl();
    requestAnimationFrame(() => this.inputTarget.form.requestSubmit());
  }

  submit(event) {
    if (this.authenticatedValue) {
      this.buttonTarget.disabled = true;
      this.buttonTarget.setAttribute('aria-busy', 'true');
      this.buttonTarget.textContent = 'Finding people…';
      return;
    }

    event.preventDefault();
    this.rememberJobUrl();
    this.open();
  }

  open() {
    if (!this.hasDialogTarget) {
      return;
    }

    document.documentElement.classList.add('tl-modal-open');
    this.dialogTarget.showModal();
  }

  close() {
    this.dialogTarget.close();
  }

  backdrop(event) {
    if (event.target === this.dialogTarget) {
      this.close();
    }
  }

  closed() {
    document.documentElement.classList.remove('tl-modal-open');
  }

  disconnect() {
    document.documentElement.classList.remove('tl-modal-open');
  }

  rememberJobUrl() {
    if (!this.hasInputTarget) {
      return;
    }

    try {
      sessionStorage.setItem('talentleads.pendingJobUrl', this.inputTarget.value);
    } catch (_error) {
      // The modal still works when browser storage is unavailable.
    }
  }

  pendingJobUrl() {
    try {
      return sessionStorage.getItem('talentleads.pendingJobUrl');
    } catch (_error) {
      return null;
    }
  }

  clearPendingJobUrl() {
    try {
      sessionStorage.removeItem('talentleads.pendingJobUrl');
    } catch (_error) {
      // Nothing to clear when browser storage is unavailable.
    }
  }
}
