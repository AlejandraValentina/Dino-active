"""Original-byte and portable-project regressions using genuine preserved endpoints.

No solver run is generated here. Test-created corruptions never touch originals.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from motorsim.dino4t.artifacts import json_bytes, parse_json, safe_path, sha256, verify_primary
from motorsim.desktop.four_stroke_artifacts import (
    assess_run_reference, require_verified_run, reconstruct_from_ab_receipt,
    export_project_bundle, import_reference_bundle, recover_recorded_text_bytes)
from motorsim.desktop.four_stroke_comparison import build_comparison, ComparisonIneligible
from motorsim.desktop.four_stroke_project import create_project
from motorsim.engine_project import load_project

ROOT = Path('results/dino4t-ab-engineering-v1/runs')
RECEIPT = ROOT/'comparison.json'


@pytest.mark.parametrize('raw',[b'{"x":1e999}',b'{"x":NaN}',b'{"x":1,"x":2}'])
def test_strict_json_rejects_nonfinite_and_duplicate_fields(raw):
    with pytest.raises(ValueError):parse_json(raw)


@pytest.fixture
def reconstructed(tmp_path):
    receipt = parse_json(RECEIPT.read_bytes()); refs=[]
    for side, endpoint in zip(('A','B'), receipt['endpoints']):
        source=ROOT/'runs'/endpoint['run_id']/'artifacts'/'summary.json'
        refs.append(reconstruct_from_ab_receipt(source,RECEIPT,sha256(RECEIPT.read_bytes()),
            endpoint['run_id'],tmp_path/side,'receipt-study',byte_recovery_policy='GIT_TEXT_RECORDED_EOL_V1'))
    return refs


def test_original_receipt_binds_artifacts_without_retroactive_source_promotion(reconstructed):
    a,b=map(require_verified_run,reconstructed)
    assert a.meta['source_qualification']=='SOURCE_IDENTITY_UNVERIFIED_LEGACY'
    assert a.meta['artifact_origin']['role_authority']['config'].startswith('ORIGINAL_CANONICAL')
    with pytest.raises(ComparisonIneligible,match='inventario original completo'):
        build_comparison(a.endpoint(),b.endpoint())
    compared=build_comparison(a.endpoint(),b.endpoint(),policy='LEGACY_RECEIPT_DESCRIPTIVE_V1')
    assert compared['classification']=='LEGACY_SOURCE_UNVERIFIED_MODEL_SENSITIVITY'
    assert compared['endpoints'][0]['artifact_origin']['evidence_sha256']==sha256(RECEIPT.read_bytes())
    old=parse_json(RECEIPT.read_bytes())
    assert compared['metrics']==old['metrics']
    assert compared['comparison_id']!=old['comparison_id']  # version/provenance changed, never force oldID


def test_portable_project_reopens_after_original_bundle_location_disappears(tmp_path,reconstructed):
    a,b=map(require_verified_run,reconstructed)
    comparison_id=build_comparison(a.endpoint(),b.endpoint(),policy='LEGACY_RECEIPT_DESCRIPTIVE_V1')['comparison_id']
    project=create_project('receipt-study',a.config,variants={b.config['identifier']:b.config},run_references=reconstructed)
    exported=export_project_bundle(project,tmp_path/'bundle')
    shutil.copytree(exported.parent,tmp_path/'elsewhere')
    exported.parent.rename(tmp_path/'old-location-unavailable')
    Path(reconstructed[0]['run_manifest_path']).parent.rename(tmp_path/'old-A-unavailable')
    Path(reconstructed[1]['run_manifest_path']).parent.rename(tmp_path/'old-B-unavailable')
    reopened=load_project(tmp_path/'elsewhere'/'project.dino.json')
    aa,bb=map(require_verified_run,reopened['run_references'])
    assert aa.reference['run_manifest_sha256']==a.reference['run_manifest_sha256']
    assert build_comparison(aa.endpoint(),bb.endpoint(),policy='LEGACY_RECEIPT_DESCRIPTIVE_V1')['comparison_id']==comparison_id


def test_trace_or_nested_manifest_rebinding_cannot_bypass_original_outer_digest(reconstructed):
    ref=reconstructed[0];verified=require_verified_run(ref)
    path=verified.snapshot['paths']['trace'];path.write_bytes(path.read_bytes().replace(b',',b',9',1))
    assert not assess_run_reference(ref).verified
    manifest_path=verified.snapshot['manifest_path'];manifest=deepcopy(verified.snapshot['manifest'])
    manifest['artifacts']['trace'].update(sha256=sha256(path.read_bytes()),size_bytes=path.stat().st_size)
    manifest_path.write_bytes(json_bytes(manifest))
    assert not assess_run_reference(ref).verified


def test_metadata_redirection_is_bound_and_loaded_plot_uses_immutable_snapshot(reconstructed):
    ref=reconstructed[0];verified=require_verified_run(ref)
    original=verified.snapshot['raw']['trace']
    verified.snapshot['paths']['trace'].write_bytes(b'theta,p\n0,4200000\n')
    assert verified.snapshot['raw']['trace']==original
    assert not assess_run_reference(ref).verified


def test_malformed_known_digest_objects_are_structured_rejections(tmp_path,reconstructed):
    bad=tmp_path/'artifacts.json';bad.write_bytes(b'[]')
    with pytest.raises(ValueError,match='object'):verify_primary(bad,sha256(b'[]'))
    ref=deepcopy(reconstructed[0]);Path(ref['run_manifest_path']).write_bytes(b'[]')
    ref['run_manifest_sha256']=sha256(b'[]')
    assert assess_run_reference(ref).classification=='CORRUPT_OR_INCOMPATIBLE'


@pytest.mark.parametrize('path',['../x','a/../x','x//y','./x','C:/x','x\\y'])
def test_inner_paths_are_canonical_relative_and_host_independent(tmp_path,path):
    with pytest.raises(ValueError):safe_path(tmp_path,path)


def test_case_aliases_are_rejected_before_reading_another_role(reconstructed):
    original=require_verified_run(reconstructed[0]);manifest=deepcopy(original.snapshot['manifest'])
    manifest['artifacts']['config']['path']='SUMMARY.JSON'
    path=original.snapshot['manifest_path'];path.write_bytes(json_bytes(manifest))
    with pytest.raises(ValueError,match='case-aliased'):verify_primary(path,sha256(path.read_bytes()))


def test_explicit_EOL_recovery_requires_an_original_expected_digest():
    lf=b'{"sample": 1}\n';crlf=lf.replace(b'\n',b'\r\n')
    with pytest.raises(ValueError):recover_recorded_text_bytes(lf,sha256(crlf),None)
    assert recover_recorded_text_bytes(lf,sha256(crlf),'GIT_TEXT_RECORDED_EOL_V1')==crlf
    with pytest.raises(ValueError):recover_recorded_text_bytes(lf,'0'*64,'GIT_TEXT_RECORDED_EOL_V1')


def test_reference_import_requires_the_external_original_anchor_not_adjacent_hash(tmp_path,reconstructed):
    reference=deepcopy(reconstructed[0]);source=tmp_path/'external-reference.json'
    source.write_bytes(json_bytes(reference))
    imported=import_reference_bundle(source,tmp_path/'imported')
    assert require_verified_run(imported).reference['run_manifest_sha256']==reference['run_manifest_sha256']
    manifest=tmp_path/'adjacent-manifest.json';manifest.write_bytes(b'{"schema":"DINO4T_ARTIFACT_MANIFEST_V1"}')
    with pytest.raises(ValueError,match='outer reference'):import_reference_bundle(manifest,tmp_path/'not-admitted')
