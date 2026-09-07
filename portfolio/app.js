(() => {
  const links = [...document.querySelectorAll('.example-link')];
  const examples = [...document.querySelectorAll('.example')];
  const show = () => {
    const requested = window.location.hash.slice(1);
    const selected = examples.find(item => item.id === requested) || examples[0];
    examples.forEach(item => { item.hidden = item !== selected; });
    links.forEach(link => {
      if (link.hash === '#' + selected.id) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    });
  };
  document.documentElement.classList.add('js');
  show();
  links.forEach(link => link.addEventListener('click', event => {
    event.preventDefault();
    history.pushState(null, '', link.hash);
    show();
  }));
  window.addEventListener('hashchange', show);
  window.addEventListener('popstate', show);
})();
