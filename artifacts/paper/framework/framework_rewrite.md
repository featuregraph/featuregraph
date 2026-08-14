## Framework

The research question behind this study is: "If LLM access were gone tomorrow, what could researchers maintain from their LLM-assisted analyses? An LLM conversation can produce a useful analysis, but a conversation is not a durable computational representation of the analysis. 

We can split the success of a representation into two parts: whether it is durable, and whether it generalizes. A representation that does not generalize is not useful. We want to be able to reproduce the results of an analysis not only in our own work, but in other domains as well.

One of the continuing struggles we have in data analysis is having to reproduce the same takss over and over without being able to store our reasoning process and repeat it in ways that will give us solutions with similar levels of rigor and precision each time. 

A reasoning process that had its own form of represenation that it could apply readily to a class of problems would potentially save itself a great deal of repeated computation. If we could embed parts of our reasooning into a graph and embody them through computation, we would not have to keep repeating the same analyses.

Define:

Representation

Preservation vs transfer

Separate:

Durability

Inspectability

Transfer

The BIDMC study succeeded strongly on durability and inspectability but only partially on transfer

A representation system can take implicit information from a timeseries signal and make it explicit. A reasoning system faced with timeseries data and asked to discover patterns and relationships within it can be aided greatly by having some of the relationships within the data made explicit.

Among domain practitioners this is often an ad-hoc, individual process of a knowledgeable expert encoding relationships between parts of the data they already know well. Much of their work is not immediately applicable to similar problems or accessible to other experts with different views of the data available to them. If I cannot understand or recreate your code, I often cannot reproduce your work and the conclusions you have reached will often be frustratingly inaccessible to me.

As researchers we have a few options available to us. We can make the intermediate results of our analyses available to others. I can take your timeseries data, give you back a list of aggregations, and make them queryable to you, so that you never need to carry out that process yourself.

(Next thought: I can create a representational system for your data that will also apply to other people’s data…)

The primary complaint is that what disappears when an analysis is complete is much of the representation we would like to be able to recreate for that problem or similar problems. If you’ve already modeled a signal as a collection of states, boundaries, and behaviors, others would like to be able to use your representation of that signal without having to reproduce it. If you’ve already derived properties from the signal such as how much it’s physically accumulated over a time period, others would like that representation available to them. 

