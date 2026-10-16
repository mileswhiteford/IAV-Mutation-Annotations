# Decisions and Protocol Changes

As we annotate, we will almost certainly change parts of this protocol and the schema. Those changes need to be written down so that both of us are annotating by the same rules, and so we can tell later which rules a given row was annotated under.

**When we change anything in this file, the schema, the vocabulary, or anything noteworthy:**

1. Add an entry at the top of `DECISIONS.md` — today's date, what
   changed, and why.
2. If the change means rows already annotated need re-checking, say so
   in the entry.
3. Mention the change in the commit message.

**Include the date annotated for all annotation records.** That way we can easily see which may need to be reannotated. 

To find out which rules a row followed, look at `DECISIONS.md` for entries dated before that row.

# Annotation Protocol:
Last Updated: 10/15/2026

## Source Usage

- Use the **Results** section as the sole source for mutation–phenotype relationships.
- Use the **Methods** section to clarify experimental context, including viral strains, recombinant viruses, cell types, animal models, receptor substrates, temperatures, and numbering schemes.

## Inclusion Criteria

- Include all experimentally tested amino-acid mutations or mutation combinations with observed effects relevant to mammalian host adaptation.
- Include every relevant (mammalian host adaptive) mutation–phenotype relationship, not just the most prominent findings.
- Treat each unique combination of mutation(s), phenotype, and experimental system as a separate observation.
- If a mutation produces multiple relevant phenotypes, record each phenotype separately.
- Keep mutations tested together as a combination unless their individual effects were separately tested and reported.
- Treat experiments conducted in different experimental contexts as a separate observations. For example, different viral backbones, strains, subtypes, assays, cell types, animal models, receptor-binding systems, or temperatures.

## Exclusion Criteria

Exclude the following:

- Background claims or findings cited from previous studies.
- Predicted, inferred, or computationally proposed mutation effects without experimental validation.
- Mutations for which no phenotypic effect was observed.
- General virulence-only outcomes, including pathogenicity, mortality, morbidity, or weight loss.
- Mutations related to antibody, antiviral drug, or vaccine resistance.
- Mutations with unspecified amino-acid identities or positions.
