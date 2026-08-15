---

## Ongoing notes

Define:

Representation - done

Preservation vs transfer

Separate:

Durability

Inspectability

Transfer

The BIDMC study succeeded strongly on durability and inspectability but only partially on transfer

A representation system can take implicit information from a timeseries signal and make it explicit. A reasoning system faced with timeseries data and asked to discover patterns and relationships within it can be aided greatly by having some of the relationships within the data made explicit.

Among domain practitioners this is often an ad-hoc, individual process of a knowledgeable expert encoding relationships between parts of the data they already know well. Much of their work is not immediately applicable to similar problems or accessible to other experts with different views of the data available to them. If I cannot understand or recreate your code, I often cannot reproduce your work and the conclusions you have reached will often be frustratingly inaccessible to me.

As researchers we have a few options available to us. We can make the intermediate results of our analyses available to others. I can take your timeseries data, give you back a list of aggregations, and make them queryable to you, so that you never need to carry out that process yourself.

The primary complaint is that what disappears when an analysis is complete is much of the representation we would like to be able to recreate for that problem or similar problems. If you’ve already modeled a signal as a collection of states, boundaries, and behaviors, others would like to be able to use your representation of that signal without having to reproduce it. If you’ve already derived properties from the signal such as how much it’s physically accumulated over a time period, others would like that representation available to them. 

