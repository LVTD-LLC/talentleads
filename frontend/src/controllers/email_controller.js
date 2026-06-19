import { Controller } from "@hotwired/stimulus";

export default class extends Controller {
  static targets = ["emailTemplate", "sendEmailButton", "sendEmailForm"];

  connect() {
    this.updateSendEmail();
  }

  updateSendEmail() {
    const selectedOption = this.emailTemplateTarget.selectedOptions[0];
    const sendUrl = selectedOption ? selectedOption.dataset.sendUrl : null;

    if (!sendUrl) {
      this.sendEmailButtonTarget.disabled = true;
      return;
    }

    this.sendEmailFormTarget.action = sendUrl;
    this.sendEmailButtonTarget.disabled = false;
  }

  submit(event) {
    if (this.submitting) {
      event.preventDefault();
      return;
    }

    this.submitting = true;
    this.sendEmailButtonTarget.disabled = true;
    this.sendEmailButtonTarget.textContent = "Sending outreach...";
  }
}
