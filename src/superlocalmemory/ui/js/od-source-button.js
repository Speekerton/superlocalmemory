// A native source trigger, with its expandable detail outside the button.
(function () {
  'use strict';
  window.slmSourceRow = function (id, label) {
    var row = document.createElement('div');
    row.className = 'fact-result-item'; row.dataset.factId = id;
    var button = document.createElement('button');
    button.type = 'button'; button.className = 'btn sm ghost'; button.textContent = label;
    button.addEventListener('click', function () {
      // fact-detail delegates on the row and excludes nested action buttons.
      row.click();
    });
    row.appendChild(button);
    return row;
  };
}());
