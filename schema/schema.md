
# Schema Definitions

## author

The CIEER Researcher (Usually first or last author) who will be reviewing their paper. 

## paper_id

Our ID for each paper. Makes it easier to keep track and collaborate. Check `papers.csv` for paper id.

## backbone

The viral strain or genetic backbone in which the mutation was experimentally tested.

- Use the full strain name whenever available.
- Avoid use abbreviated strain names or laboratory nicknames when possible.
- Only use the strain name mentioned in the paper. If a strain nickname has a known full strain name, but the full strain name is not mentioned in the paper, use the nickname.  
- For reassortant or recombinant viruses, identify the genetic backbone rather than the source of an introduced gene.

**Example:** 
- `"A/Vietnam/1204/2004"`

## recombinant

The donor strain(s) introduced into the tested viral backbone.

- Use the full strain name followed by the introduced protein or segment in parentheses.
- When multiple donor strains or proteins are involved, record each as comma separated value.
- Like with backbones, avoid using recombinant nicknames when possible. 

**Examples:** 
- `A/Egypt/N02039/2009(HA)`
- `A/Vietnam/1203/2004(HA), A/Vietnam/1203/2004(NA)`

## subtype

The influenza subtype of the experimentally tested virus.

**Examples:** 
- `"H1N1"`
- `"H3N2"`
- `"H5N1"`

## protein

The influenza viral protein(s) containing the experimentally tested mutations.

- Use standard influenza protein abbreviations.
- Include all proteins involved as comma separated values when mutations occur in multiple proteins.

**Examples:** 
- `PB2`
- `HA, NA`

## mutation

The amino-acid substitution(s), deletion(s), or insertion(s) experimentally tested.

- Use the format `Protein:OriginalResiduePositionNewResidue`.
- Use single-letter amino-acid notation.
- Include all mutations tested as a combination.
- Do not separate combined mutations unless their individual effects were independently tested.
- Do not infer missing amino-acid identities or positions.

**Examples:**

- Substitution: `PB2:E627K`
- Multiple substitutions: `PB2:E627K, "PB2:D701N`
- Deletion: `HA:K111-`
- Insertion: `HA:-111Y`

## numbering

HA or NA numbering system. Only include when mutation occurs in NA or HA

- Record only explicitly stated HA or NA numbering schemes.
- Do not infer a numbering scheme if not mentioned in the text. 
- Leave unspecified when no numbering convention is provided.

**Examples:** 
- `H3`
- `N2`
  
## phenotype

The experimentally observed effect of the mutation relevant to mammalian host adaptation.

- Keep descriptions concise while preserving their biological meaning.
- Record distinct phenotypes separately.
- State the direction of the effect when reported.
- Do not include general virulence-only outcomes such as mortality, morbidity, pathogenicity, or weight loss.
- Do not include any information that can be reasonably assumed from another field (e.g. Instead of saying "Enhanced replication in mice" just report "Enhanced replication." "Mice" is reported in the animal_model field. 

**Examples:**

- `Increased polymerase activity`
- `Enhanced replication`
- `Increased binding to α2,6-linked sialic acid receptors`
- `Reduced binding to α2,3-linked sialic acid receptors`
- `Increased airborne transmission`

## cell_type

The cell line, primary cell type, tissue culture, or ex vivo cellular system used to evaluate the mutation.

- Use only for in vitro or ex vivo experiments.
- Record the specific cell type or cell line when available.
- Preserve distinctions between different cell types or cellular systems.

**Examples:** 
- `MDCK`
- `A549`
- `HEK`

## animal_model

The animal species, strain, or lineage used in an in vivo experiment.

- Use only for in vivo experiments.
- Include the specific animal strain or lineage when reported.

**Examples:** 
- `BALB/c mice`
- `Ferrets`

## binding_assay

The receptor, glycan, or receptor analog used to measure viral receptor binding.

- Use only for receptor-binding experiments.

**Examples:** 
- `3′SLN`
- `6′SLN-PAA`

## temperature

The experimental temperature at which the mutation–phenotype relationship was evaluated.

- Include the temperature only when explicitly reported.
- Record temperatures in degrees Celsius.
- Treat results obtained at different temperatures as separate experimental observations.
- Celsius is assumed 

**Examples:** 
- `33`
- `37`

## date

Date of annotation in month/day/year format. Useful for tracking changes to the annotation protocol and vocabulary.

**Example:**
- `10/16/2026`
