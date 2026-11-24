// Out points are exclusive. Decimal times are rounded once to the common 24 fps clock.
export const fps = 24;
export const cut = [
  [0, 'streetCrew', 'street'], [3.3, 'streetNed', 'street'],
  [5.3, 'bedNight', 'bedroom'], [6.65, 'black'], [7, 'wake', 'bedroom'],
  [9.7, 'clock', 'bedroom'], [14, 'chapterOne'], [15, 'pianoHands', 'ballroom'],
  [21.5, 'depotHands', 'depot'], [25.5, 'depotWide', 'depot'], [27.5, 'black'],
  [28, 'chapterTwo'], [29, 'coachDoor', 'coach'], [31, 'coachWindow', 'coach'],
  [33, 'payphone', 'phone'], [38.75, 'reset', 'bedroom'], [42, 'faresBye', 'lobby'],
  [45, 'faresTake', 'lobby'], [49, 'faresPocket', 'bedroom'], [52, 'greeting', 'lobby'],
  [57, 'curtain', 'bedroom'], [62, 'curled', 'bedroom'], [67, 'shoe', 'bedroom'],
  [69, 'rooftops', 'street'], [71, 'boothWork', 'booth'], [74, 'wheel', 'street'],
  [76.1, 'policy', 'street'], [78.3, 'waits', 'street'], [82.5, 'signs', 'street'],
  [85, 'follows', 'street'], [88.6, 'desk', 'lobby'], [94, 'switcher', 'booth'],
  [97, 'chair', 'ballroom'], [99, 'twoBars', 'ballroom'], [103, 'black'],
  [103.25, 'warmWake', 'bedroom'], [105, 'warmClock', 'bedroom'], [108, 'end']
].map(([time,id,root])=>({frame:Math.round(time*fps),id,root}));
export const unitFor = {street:'exteriors',depot:'exteriors',coach:'exteriors',phone:'exteriors',bedroom:'hotel',lobby:'hotel',ballroom:'music',booth:'music'};
