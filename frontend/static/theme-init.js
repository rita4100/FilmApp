(function () {
  try {
    var t = localStorage.getItem('filmapp-theme');
    document.documentElement.setAttribute('data-theme', t === 'light' || t === 'dark' ? t : 'dark');
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
})();
