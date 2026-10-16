// "Add row" for Django formsets: clones the empty form from <template data-formset-empty>,
// swaps __prefix__ for the next index and bumps the management form's TOTAL_FORMS.
(function () {
  const addButton = document.querySelector('[data-formset-add]');
  if (!addButton) return;

  const form = addButton.closest('form');
  const body = form.querySelector('[data-formset-body]');
  const template = form.querySelector('template[data-formset-empty]');
  const totalForms = form.querySelector('input[name$="-TOTAL_FORMS"]');

  addButton.addEventListener('click', () => {
    const index = Number(totalForms.value);
    const html = template.innerHTML.replaceAll('__prefix__', String(index));
    body.insertAdjacentHTML('beforeend', html);
    totalForms.value = String(index + 1);
    body.lastElementChild.querySelector('select, input:not([type="hidden"])')?.focus();
  });
})();
