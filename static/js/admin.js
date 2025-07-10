document.addEventListener('DOMContentLoaded', function(){
  console.log("Admin JS loaded");
  var isOpenToAll = document.getElementById('is_open_to_all');
  var startRoll = document.getElementById('start_roll_number');
  var endRoll = document.getElementById('end_roll_number');
  var rollRangeFields = document.getElementById('roll-range-fields');
  function setDisabledState() {
    if (!isOpenToAll || !startRoll || !endRoll) {
      console.log('One or more elements not found:', {isOpenToAll, startRoll, endRoll});
      return;
    }
    var disabled = isOpenToAll.checked;
    startRoll.disabled = disabled;
    endRoll.disabled = disabled;
    startRoll.readOnly = disabled;
    endRoll.readOnly = disabled;
    if (disabled) {
      startRoll.classList.add('bg-light');
      endRoll.classList.add('bg-light');
      console.log('Fields disabled');
    } else {
      startRoll.classList.remove('bg-light');
      endRoll.classList.remove('bg-light');
      console.log('Fields enabled');
    }
  }
  if (isOpenToAll) {
    isOpenToAll.addEventListener('change', setDisabledState);
    setDisabledState(); // Initial state
  } else {
    console.log('Toggle not found');
  }
  // Extra: force update on page show (for bfcache)
  window.addEventListener('pageshow', setDisabledState);
});
