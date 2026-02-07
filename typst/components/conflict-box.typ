// Conflict callout box component
// Renders disagreements between sources as a highlighted box.

#let conflict-box(topic: "", positions: (), resolution: none) = {
  block(
    width: 100%,
    inset: 12pt,
    radius: 4pt,
    fill: rgb("#FFF3CD"),
    stroke: 1pt + rgb("#FFCA2C"),
  )[
    #text(weight: "bold", size: 10pt, fill: rgb("#664D03"))[Disputed: #topic]
    #v(0.5em)
    #for pos in positions [
      - *#pos.source*: #pos.claim
        #if pos.keys().contains("citation") [
          #text(size: 9pt, fill: gray)[(#pos.citation)]
        ]
    ]
    #if resolution != none [
      #v(0.5em)
      #text(style: "italic")[Resolution: #resolution]
    ]
  ]
}
