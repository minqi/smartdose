// var width = 200;
// var height = 100;
// var x = d3.scale.linear().range([0, width]);
// var y = d3.scale.linear().range([height, 0]);
// var parseDate = d3.time.format("%e-%b-%y").parse;
// var line = d3.svg.line()
//              .interpolate("basis")
//              .x(function(d) { return x(d.date); })
//              .y(function(d) { return y(d.close); });

// function sparkline(elemId, data) {
//   data.forEach(function(d) {
//     d.date = parseDate(d.Date);
//     d.close = +d.Close;
//     console.log(d.close)
//   });
//   x.domain(d3.extent(data, function(d) { return d.date; }));
//   y.domain(d3.extent(data, function(d) { return d.close; }));

//  var svg = d3.select(elemId)
//               .append('svg')
//               .attr('width', width)
//               .attr('height', height)
//               .append('g')
//               .attr('transform', 'translate(-2, 2)');
//   svg.append('path')
//      .datum(data)
//      .attr('class', 'sparkline')
//      .attr('d', line);
//   svg.append('circle')
//      .attr('class', 'sparkcircle')
//      .attr('cx', x(data[0].date))
//      .attr('cy', y(data[0].close))
//      .attr('r', 1.5); 
// }

// d3.csv('/static/csv/vod.csv', function(error, data) {
//   console.log(data)
//   sparkline('#spark-vod', data);
// });