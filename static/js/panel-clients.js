// "Szukaj w bazie klientek" on the new-appointment form: suggestions from /panel/clients/search/,
// picking one fills name, phone and e-mail. Typing the details by hand still works.
(function () {
  const box = document.querySelector('[data-client-search]');
  if (!box) return;

  const input = box.querySelector('input[type="search"]');
  const list = box.querySelector('[role="listbox"]');
  const form = box.closest('form');
  let timer = null;
  let request = 0;

  function close() {
    list.hidden = true;
    input.setAttribute('aria-expanded', 'false');
  }

  function fill(client) {
    form.querySelector('[name="client_name"]').value = client.name;
    form.querySelector('[name="client_phone"]').value = client.phone;
    form.querySelector('[name="client_email"]').value = client.email;
    input.value = client.name;
    close();
  }

  function render(clients) {
    list.replaceChildren();
    if (!clients.length) {
      const empty = document.createElement('div');
      empty.className = 'list-group-item small text-muted';
      empty.textContent = 'Brak w bazie. Wpisz dane poniżej.';
      list.appendChild(empty);
    }
    clients.forEach((client) => {
      const option = document.createElement('button');
      option.type = 'button';
      option.className = 'list-group-item list-group-item-action';
      option.setAttribute('role', 'option');
      const name = document.createElement('strong');
      name.textContent = client.name;
      const details = document.createElement('span');
      details.className = 'small text-muted ms-2';
      details.textContent = [client.phone_display, client.email].filter(Boolean).join(', ');
      option.append(name, details);
      option.addEventListener('click', () => fill(client));
      list.appendChild(option);
    });
    list.hidden = false;
    input.setAttribute('aria-expanded', 'true');
  }

  async function search() {
    const q = input.value.trim();
    if (q.length < 2) return close();
    const current = ++request; // answers can come back out of order; only the latest one counts
    const response = await fetch(`${box.dataset.clientSearch}?q=${encodeURIComponent(q)}`);
    if (!response.ok || current !== request) return;
    render((await response.json()).clients);
  }

  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(search, 200);
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') close();
    if (e.key === 'ArrowDown' && !list.hidden) {
      e.preventDefault();
      list.querySelector('button')?.focus();
    }
  });
  list.addEventListener('keydown', (e) => {
    const options = [...list.querySelectorAll('button')];
    const i = options.indexOf(document.activeElement);
    if (e.key === 'ArrowDown' && i < options.length - 1) options[i + 1].focus();
    else if (e.key === 'ArrowUp') (i > 0 ? options[i - 1] : input).focus();
    else if (e.key === 'Escape') {
      close();
      input.focus();
    } else return;
    e.preventDefault();
  });
  document.addEventListener('click', (e) => {
    if (!box.contains(e.target)) close();
  });
})();
