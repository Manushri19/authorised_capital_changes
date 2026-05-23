"""
test_sh7_extractor_mini_llm.py
================================
Mini LLM test: injects synthetic SH-7 sample data (reflecting actual documents)
and runs run_sh7_extractor against Gemini 2.5 Flash.
"""

import os
os.environ["GOOGLE_API_KEY"] = "dummy"

from authorised_capital_changes.schemas.document import (
    ClassifiedDocument, DocumentGroup, DocumentType, FileMetadata, OfficialStatus,
)
from authorised_capital_changes.schemas.pipeline_state import PipelineState
from authorised_capital_changes.pipeline.nodes.sh7_extractor import run_sh7_extractor

# Mirrors SH7_Event2_2019.md structure
SH7_SAMPLE = """\
# FORM NO. SH-7

**Notice to Registrar of any alteration of share capital**

1.(a)* Corporate identity number (CIN) of the company | U85123DL2018PTC312456 | Pre-fill

2.(a) Name of the company | NEXUS BRIGHTLEARN SOLUTIONS PRIVATE LIMITED
(b) Address of the registered office of the company | KRISHNA TOWER PLOT NO-45 SECTOR-12 DWARKA NEW DELHI Delhi 110075
(c) * email Id of the company | arunsethi@outlook.com

3. * Purpose of the form
⊙ Increase in share capital independently by company

4. In accordance with section 61(1) of the Companies Act, 2013, that by ⊙ Ordinary ○ Special resolution at
the meeting of the members of the company held on | 15/05/2019 | (DD/MM/YYYY)

(a)(i) The authorised share capital of the company has been increased from

<table>
  <thead>
    <tr>
        <th>Existing</th>
        <th>(in Rs.)</th>
        <th>3,00,000.00</th>
    </tr>
  </thead>
    <tr>
        <td>Revised</td>
        <td>(in Rs.)</td>
        <td>50,00,000.00</td>
    </tr>
  <tr>
        <td>Difference (addition)</td>
        <td>(in Rs.)</td>
        <td>47,00,000.00</td>
    </tr>
</table>

9. Revised capital structure after taking into consideration the changes vide points 4, 5, 6 and 8 above

(a) Authorised capital of the company (in Rs.) 50,00,000.00

Break up of Authorised capital

<table>
  <tbody>
    <tr>
        <td>Number of equity shares</td>
        <td>5,00,000</td>
        <td>Total amount of equity shares (in Rs.)</td>
        <td>50,00,000.00</td>
    </tr>
  <tr>
        <td>Nominal amount per equity share</td>
        <td>10</td>
        <td></td>
        <td></td>
    </tr>
  <tr>
        <td>Number of preference shares</td>
        <td>0</td>
        <td>Total amount of preference shares (in Rs.)</td>
        <td>0.00</td>
    </tr>
  <tr>
        <td>Nominal amount per preference share</td>
        <td>0</td>
        <td></td>
        <td></td>
    </tr>
  </tbody>
</table>

(b) Issued capital of the company (in Rs.) 50,00,000.00
(c) Subscribed capital (in Rs.) 50,00,000.00
(d) Paid up capital (in Rs.) 50,00,000.00

11. Particulars of payment of stamp duty
(a) State or Union territory: Delhi
Amount of stamp duty to be paid (in Rs.) 4,700

## Attachments

<table>
  <tbody>
    <tr>
        <td>List of attachments</td>
        <td colspan="2"></td>
    </tr>
  <tr>
        <td>(5) Altered memorandum of association;</td>
        <td>Attach</td>
        <td>CTC_EGM_2019.pdf</td>
    </tr>
  <tr>
        <td>MOA_2019.pdf</td>
        <td colspan="2"></td>
    </tr>
  <tr>
        <td>CTC_Board Meeting_2019.pdf</td>
        <td colspan="2"></td>
    </tr>
  </tbody>
</table>

## Declaration
I ARUN VIKRAM SETHI, Director declare all requirements complied with.

**For office use only:**
eForm Service request number (SRN) H45678902 eForm filing date 15/05/2019 (DD/MM/YYYY)
"""


def _make_group(filename: str, content: str) -> DocumentGroup:
    doc = ClassifiedDocument(
        file_metadata=FileMetadata(
            filename=filename,
            filepath=f"/tmp/{filename}",
            raw_content=content,
            file_size_bytes=len(content),
        ),
        document_type=DocumentType.SH7,
        official_status=OfficialStatus.OFFICIAL,
        classification_method="rule_based",
        classification_confidence=0.92,
        event_date_hint=None,
        cin_hint=None,
        requires_human_review=False,
        review_reason=None,
    )
    return DocumentGroup(
        event_index=2,
        sh7=doc,
        board_resolution=None,
        egm_resolution=None,
        moa=None,
        unmatched_attachment_refs=[],
    )


def test_mini_llm():
    state: PipelineState = {
        "document_groups": [_make_group("SH7_Event2_2019.md", SH7_SAMPLE)],
        "pipeline_errors": [],
        "completed_stages": [],
        "sh7_extraction_errors": [],
    }

    print("Running SH-7 Extractor mini LLM test...")
    result = run_sh7_extractor(state)

    extractions = result["extracted_sh7s"]
    print(f"\nExtractions: {len(extractions)}")

    e = extractions[0]
    print(f"\nCIN                       : {e.cin}")
    print(f"Company Name              : {e.company_name}")
    print(f"Email                     : {e.email}")
    print(f"Purpose                   : {e.purpose}")
    print(f"Meeting Date              : {e.meeting_date}")
    print(f"Resolution Type           : {e.resolution_type}")
    print(f"Existing Auth Capital     : {e.existing_authorised_capital}")
    print(f"Revised Auth Capital      : {e.revised_authorised_capital}")
    print(f"  9(a) Total              : {e.authorised_capital.total_amount}")
    print(f"  9(a) Equity Shares      : {e.authorised_capital.breakdown.equity_shares_count}")
    print(f"  9(a) Nominal/Share      : {e.authorised_capital.breakdown.equity_nominal_per_share}")
    print(f"  9(a) Pref Shares        : {e.authorised_capital.breakdown.preference_shares_count}")
    print(f"SRN                       : {e.srn}")
    print(f"Filing Date               : {e.filing_date}")
    print(f"Stamp Duty State          : {e.stamp_duty_state}")
    print(f"Stamp Duty Amount         : {e.stamp_duty_amount}")
    print(f"Attachment Filenames      : {e.attachment_filenames_raw}")
    print(f"Confidence                : {e.extraction_confidence:.2f}")
    print(f"Unconfirmed Fields        : {e.unconfirmed_fields}")
    print(f"Extraction Errors         : {e.extraction_errors}")

    if result["sh7_extraction_errors"]:
        print(f"\nsh7_extraction_errors: {result['sh7_extraction_errors']}")
    else:
        print("\nNo extraction errors.")

    print(f"Completed stages: {result['completed_stages']}")


if __name__ == "__main__":
    test_mini_llm()
