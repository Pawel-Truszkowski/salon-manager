// Bootstrap tabs/pills that remember the selected tab in the URL hash (`<ul data-hash-tabs>` + `data-hash` on each
// button). Reloading, coming back after a save (the server redirects to `...#<hash>`) or sharing the link
// opens the same tab. Panes use a different id than the hash, so the browser doesn't jump-scroll to them.
(function () {
  document.querySelectorAll('[data-hash-tabs]').forEach((list) => {
    const buttons = [...list.querySelectorAll('[data-hash]')];
    const fromHash = buttons.find((button) => button.dataset.hash === window.location.hash.slice(1));
    if (fromHash) bootstrap.Tab.getOrCreateInstance(fromHash).show();

    buttons.forEach((button) => {
      // replaceState: switching tabs shouldn't fill the Back button history
      button.addEventListener('shown.bs.tab', () => history.replaceState(null, '', `#${button.dataset.hash}`));
    });
  });
})();
