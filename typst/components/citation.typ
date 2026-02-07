// Citation formatting component

#let cite-inline(num) = {
  super(text(size: 8pt, fill: blue)[[#num]])
}

#let cite-entry(num, claim, llm, url: none) = {
  block(inset: (left: 1em))[
    #text(size: 9pt)[
      [#num] #claim \
      #text(fill: gray)[Source: #llm]
      #if url != none [
        — #link(url)[#url]
      ]
    ]
  ]
}
