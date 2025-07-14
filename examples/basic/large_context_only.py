import asyncio

from hica import Agent, ConversationMemoryStore, Thread
from hica.agent import Agent, AgentConfig

large_context = """
CRISPR gene editing (/ˈkrɪspər/; pronounced like "crisper"; an abbreviation for "clustered regularly interspaced short palindromic repeats") is a genetic engineering technique in molecular biology by which the genomes of living organisms may be modified. It is based on a simplified version of the bacterial CRISPR-Cas9 antiviral defense system. By delivering the Cas9 nuclease complexed with a synthetic guide RNA (gRNA) into a cell, the cell's genome can be cut at a desired location, allowing existing genes to be removed or new ones added in vivo.[1]

The technique is considered highly significant in biotechnology and medicine as it enables editing genomes in vivo and is precise, cost-effective, and efficient. It can be used in the creation of new medicines, agricultural products, and genetically modified organisms, or as a means of controlling pathogens and pests. It also offers potential in the treatment of inherited genetic diseases as well as diseases arising from somatic mutations such as cancer. However, its use in human germline genetic modification is highly controversial. The development of this technique earned Jennifer Doudna and Emmanuelle Charpentier the Nobel Prize in Chemistry in 2020.[2][3] The third researcher group that shared the Kavli Prize for the same discovery,[4] led by Virginijus Šikšnys, was not awarded the Nobel prize.[5][6][7]

Working like genetic scissors, the Cas9 nuclease opens both strands of the targeted sequence of DNA to introduce the modification by one of two methods. Knock-in mutations, facilitated via homology directed repair (HDR), is the traditional pathway of targeted genomic editing approaches.[1] This allows for the introduction of targeted DNA damage and repair. HDR employs the use of similar DNA sequences to drive the repair of the break via the incorporation of exogenous DNA to function as the repair template.[1] This method relies on the periodic and isolated occurrence of DNA damage at the target site in order for the repair to commence. Knock-out mutations caused by CRISPR-Cas9 result from the repair of the double-stranded break by means of non-homologous end joining (NHEJ) or POLQ/polymerase theta-mediated end-joining (TMEJ). These end-joining pathways can often result in random deletions or insertions at the repair site, which may disrupt or alter gene functionality. Therefore, genomic engineering by CRISPR-Cas9 gives researchers the ability to generate targeted random gene disruption.

While genome editing in eukaryotic cells has been possible using various methods since the 1980s, the methods employed had proven to be inefficient and impractical to implement on a large scale. With the discovery of CRISPR and specifically the Cas9 nuclease molecule, efficient and highly selective editing became possible. Cas9 derived from the bacterial species Streptococcus pyogenes has facilitated targeted genomic modification in eukaryotic cells by allowing for a reliable method of creating a targeted break at a specific location as designated by the crRNA and tracrRNA guide strands.[8] Researchers can insert Cas9 and template RNA with ease in order to silence or cause point mutations at specific loci. This has proven invaluable for quick and efficient mapping of genomic models and biological processes associated with various genes in a variety of eukaryotes. Newly engineered variants of the Cas9 nuclease that significantly reduce off-target activity have been developed.[9]

CRISPR-Cas9 genome editing techniques have many potential applications. The use of the CRISPR-Cas9-gRNA complex for genome editing[10] was the AAAS's choice for Breakthrough of the Year in 2015.[11] Many bioethical concerns have been raised about the prospect of using CRISPR for germline editing, especially in human embryos.[12] In 2023, the first drug making use of CRISPR gene editing, Casgevy, was approved for use in the United Kingdom, to cure sickle-cell disease and beta thalassemia.[13][14] Casgevy was approved for use in the United States on December 8, 2023, by the Food and Drug Administration.[15]

History
Other methods
In the early 2000s, German researchers began developing zinc finger nucleases (ZFNs), synthetic proteins whose DNA-binding domains enable them to create double-stranded breaks in DNA at specific points. ZFNs have a higher precision and the advantage of being smaller than Cas9, but ZFNs are not as commonly used as CRISPR-based methods. In 2010, synthetic nucleases called transcription activator-like effector nucleases (TALENs) provided an easier way to target a double-stranded break to a specific location on the DNA strand. Both zinc finger nucleases and TALENs require the design and creation of a custom protein for each targeted DNA sequence, which is a much more difficult and time-consuming process than that of designing guide RNAs. CRISPRs are much easier to design because the process requires synthesizing only a short RNA sequence, a procedure that is already widely used for many other molecular biology techniques (e.g. creating oligonucleotide primers).[16]

Whereas methods such as RNA interference (RNAi) do not fully suppress gene function, CRISPR, ZFNs, and TALENs provide full, irreversible gene knockout.[17] CRISPR can also target several DNA sites simultaneously simply by introducing different gRNAs. In addition, the costs of employing CRISPR are relatively low.[17][18][19]

Discovery
In 2005, Alexander Bolotin at the French National Institute for Agricultural Research (INRA) discovered a CRISPR locus that contained novel Cas genes, significantly one that encoded a large protein known as Cas9.[20]

In 2006, Eugene Koonin at the US National Center for Biotechnology information, NIH, proposed an explanation as to how CRISPR cascades as a bacterial immune system.[20]

In 2007, Philippe Horvath at Danisco France SAS displayed experimentally how CRISPR systems are an adaptive immune system, and integrate new phage DNA into the CRISPR array, which is how they fight off the next wave of attacking phage.[20]

In 2012, the research team led by professor Jennifer Doudna (University of California, Berkeley) and professor Emmanuelle Charpentier (Umeå University) were the first people to identify, disclose, and file a patent application for the CRISPR-Cas9 system needed to edit DNA.[20] They also published their finding that CRISPR-Cas9 could be programmed with RNA to edit genomic DNA, now considered one of the most significant discoveries in the history of biology.

Patents and commercialization
As of November 2013, SAGE Labs (part of Horizon Discovery group) had exclusive rights from one of those companies to produce and sell genetically engineered rats and non-exclusive rights for mouse and rabbit models.[21] By 2015, Thermo Fisher Scientific had licensed intellectual property from ToolGen to develop CRISPR reagent kits.[22]

As of December 2014, patent rights to CRISPR were contested. Several companies formed to develop related drugs and research tools.[23] As companies ramped up financing, doubts as to whether CRISPR could be quickly monetized were raised.[24] In 2014, Feng Zhang of the Broad Institute of MIT and Harvard and nine others were awarded US patent number 8,697,359[25] over the use of CRISPR–Cas9 gene editing in eukaryotes. Although Charpentier and Doudna (referred to as CVC) were credited for the conception of CRISPR, the Broad Institute was the first to achieve a "reduction to practice" according to patent judges Sally Gardner Lane, James T. Moore and Deborah Katz.[26]

The first set of patents was awarded to the Broad team in 2015, prompting attorneys for the CVC group to request the first interference proceeding.[27] In February 2017, the US Patent Office ruled on a patent interference case brought by University of California with respect to patents issued to the Broad Institute, and found that the Broad patents, with claims covering the application of CRISPR-Cas9 in eukaryotic cells, were distinct from the inventions claimed by University of California.[28][29][30]

Shortly after, University of California filed an appeal of this ruling.[31][32] In 2019 the second interference dispute was opened. This was in response to patent applications made by CVC that required the appeals board to determine the original inventor of the technology. The USPTO ruled in March 2022 against UC, stating that the Broad Institute were first to file. The decision affected many of the licensing agreements for the CRISPR editing technology that was licensed from UC Berkeley. UC stated its intent to appeal the USPTO's ruling.[33]

Recent events
In March 2017, the European Patent Office (EPO) announced its intention to allow claims for editing all types of cells to Max-Planck Institute in Berlin, University of California, and University of Vienna,[34][35] and in August 2017, the EPO announced its intention to allow CRISPR claims in a patent application that MilliporeSigma had filed.[34] As of August 2017 the patent situation in Europe was complex, with MilliporeSigma, ToolGen, Vilnius University, and Harvard contending for claims, along with University of California and Broad.[36]

In July 2018, the ECJ ruled that gene editing for plants was a sub-category of GMO foods and therefore that the CRISPR technique would henceforth be regulated in the European Union by their rules and regulations for GMOs.[37]

In February 2020, a US trial showed safe CRISPR gene editing on three cancer patients.[38]

In October 2020, researchers Emmanuelle Charpentier and Jennifer Doudna were awarded the Nobel Prize in Chemistry for their work in this field.[39][40] They made history as the first two women to share this award without a male contributor.[41][5]

In June 2021, the first, small clinical trial of intravenous CRISPR gene editing in humans concluded with promising results.[42][43]

In September 2021, the first CRISPR-edited food went on public sale in Japan. Tomatoes were genetically modified for around five times the normal amount of possibly calming[44] GABA.[45] CRISPR was first applied in tomatoes in 2014.[46]

In December 2021, it was reported that the first CRISPR-gene-edited marine animal/seafood and second set of CRISPR-edited food has gone on public sale in Japan: two fish of which one species grows to twice the size of natural specimens due to disruption of leptin, which controls appetite, and the other grows to 1.2 times the natural average size with the same amount of food due to disabled myostatin, which inhibits muscle growth.[47][48][49]

A 2022 study has found that knowing more about CRISPR tomatoes had a strong effect on the participants' preference. "Almost half of the 32 participants from Germany who are scientists demonstrated constant choices, while the majority showed increased willingness to buy CRISPR tomatoes, mostly non-scientists."[50][51]

In May 2021, UC Berkeley announced their intent to auction non-fungible tokens of both the patent for CRISPR gene editing as well as cancer immunotherapy. However, the university would in this case retain ownership of the patents.[52][53] 85 % of funds gathered through the sale of the collection named The Fourth Pillar were to be used to finance research.[54][55] It sold in June 2022 for 22 Ether, which was around US$54,000 at the time.[56]

In November 2023, the United Kingdom's Medicines and Healthcare products Regulatory Agency (MHRA) became the first in the world to approve the use of the first drug based on CRISPR gene editing, Casgevy, to treat sickle-cell anemia and beta thalassemia. Casgevy, or exagamglogene autotemcel, directly acts on the genes of the stem cells inside the patient's bones, having them produce healthy red blood cells. This treatment thus avoids the need for regular, costly blood transfusions.[13][14]

In December 2023, the FDA approved the first gene therapy in the US to treat patients with Sickle Cell Disease (SCD). The FDA approved two milestone treatments, Casgevy and Lyfgenia, representing the first cell-based gene therapies for the treatment of SCD.[57]



"""


async def main():
    # Simulate a large context (e.g., a long document)
    config = AgentConfig(
        model="openai/gpt-4.1-mini",
        system_prompt=(
            "You are an autonomous agent. Reason carefully to select tools based on their name, description, and parameters. "
            "Analyze the user input, identify the required operation, and determine if clarification is needed."
        ),
    )

    agent = Agent(config=config)
    thread = Thread()
    store = ConversationMemoryStore(backend_type="file", context_dir="context")
    thread.add_event(type="user_input", data="calculate 5+4 at the end of the summary")
    response = await agent.run_llm(
        prompt="Summarize the main findings", thread=thread, context=large_context
    )
    print("LLM response (large context only):", response)
    store.set(thread)
    print(thread.thread_id)


asyncio.run(main())
