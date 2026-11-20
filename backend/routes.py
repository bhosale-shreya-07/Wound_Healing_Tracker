import os, json, uuid, cv2
from datetime import date
from flask import Blueprint, request, jsonify, current_app, send_file, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Wound, WoundImage, Comparison
from cv.pipeline import analyze, apply_manual_polygon
from cv.compare import compare_images

bp = Blueprint("api", __name__, url_prefix="/api")


def root():
    return current_app.config["UPLOAD_DIR"]


def P(rel):
    return os.path.join(root(), rel)


def owned_wound(wid):
    w = db.session.get(Wound, wid)
    if not w or w.user_id != int(get_jwt_identity()):
        abort(404)
    return w


def write(img, wid, uid, tag):
    rel = f"{wid}/{uid}_{tag}.png"
    os.makedirs(os.path.dirname(P(rel)), exist_ok=True)
    cv2.imwrite(P(rel), img)
    return rel


def img_json(i):
    url = lambda p: f"/files/{p}" if p else None
    return dict(id=i.id, captured_on=i.captured_on.isoformat(),
                original=url(i.original_path), overlay=url(i.overlay_path),
                area_px=i.area_px, perimeter_px=i.perimeter_px,
                area_cm2=i.area_cm2, perimeter_cm=i.perimeter_cm,
                low_confidence=i.low_confidence, manually_corrected=i.manually_corrected,
                calibrated=i.px_per_cm is not None)


def sorted_images(wid):
    return (WoundImage.query.filter_by(wound_id=wid)
            .order_by(WoundImage.captured_on, WoundImage.id).all())


def refresh_comparisons(wid):
    """Re-compute comparisons between consecutive dated images."""
    imgs = sorted_images(wid)
    Comparison.query.filter_by(wound_id=wid).delete()
    load = lambda i: dict(norm=cv2.imread(P(i.normalized_path)),
                          mask=cv2.imread(P(i.mask_path), 0), area_cm2=i.area_cm2)
    for prev, curr in zip(imgs, imgs[1:]):
        r = compare_images(load(prev), load(curr))
        rel = write(r["vis"], wid, uuid.uuid4().hex, "diff")
        db.session.add(Comparison(wound_id=wid, prev_image_id=prev.id, curr_image_id=curr.id,
                                  pct_change=r["pct_change"], healed_px=r["healed_px"],
                                  grown_px=r["grown_px"], aligned=r["aligned"], diff_path=rel))
    db.session.commit()


@bp.post("/wounds")
@jwt_required()
def create_wound():
    d = request.get_json() or {}
    if not d.get("label"):
        return jsonify(error="Label required"), 400
    w = Wound(user_id=int(get_jwt_identity()), label=d["label"], body_location=d.get("body_location"))
    db.session.add(w)
    db.session.commit()
    return jsonify(id=w.id, label=w.label), 201


@bp.get("/wounds")
@jwt_required()
def list_wounds():
    ws = Wound.query.filter_by(user_id=int(get_jwt_identity())).all()
    return jsonify([dict(id=w.id, label=w.label, body_location=w.body_location) for w in ws])


@bp.post("/wounds/<int:wid>/images")
@jwt_required()
def upload(wid):
    owned_wound(wid)
    f = request.files.get("image")
    if not f:
        return jsonify(error="No image"), 400
    try:
        captured = date.fromisoformat(request.form["captured_on"])
    except Exception:
        return jsonify(error="captured_on must be YYYY-MM-DD"), 400
    calib = json.loads(request.form.get("calib") or "null")
    roi = json.loads(request.form.get("roi") or "null")

    uid = uuid.uuid4().hex
    orig_rel = f"{wid}/{uid}_orig.jpg"
    os.makedirs(os.path.dirname(P(orig_rel)), exist_ok=True)
    f.save(P(orig_rel))
    try:
        r = analyze(P(orig_rel), roi, calib)
    except ValueError as e:
        os.remove(P(orig_rel))
        return jsonify(error=str(e)), 422

    img = WoundImage(
        wound_id=wid, captured_on=captured, original_path=orig_rel,
        normalized_path=write(r["norm"], wid, uid, "norm"),
        overlay_path=write(r["overlay"], wid, uid, "overlay"),
        mask_path=write(r["mask"], wid, uid, "mask"),
        scale=r["scale"], px_per_cm=r["px_per_cm"], area_px=r["area_px"],
        perimeter_px=r["perimeter_px"], area_cm2=r["area_cm2"],
        perimeter_cm=r["perimeter_cm"], low_confidence=r["low_confidence"])
    db.session.add(img)
    db.session.commit()
    refresh_comparisons(wid)
    return jsonify(img_json(img)), 201


@bp.post("/images/<int:iid>/correct")
@jwt_required()
def correct(iid):
    img = db.session.get(WoundImage, iid) or abort(404)
    owned_wound(img.wound_id)
    poly = (request.get_json() or {}).get("polygon", [])
    if len(poly) < 3:
        return jsonify(error="Need at least 3 points"), 400
    norm = cv2.imread(P(img.normalized_path))
    r = apply_manual_polygon(norm, poly, img.scale, img.px_per_cm)
    uid = uuid.uuid4().hex
    img.mask_path = write(r["mask"], img.wound_id, uid, "mask")
    img.overlay_path = write(r["overlay"], img.wound_id, uid, "overlay")
    img.area_px, img.perimeter_px = r["area_px"], r["perimeter_px"]
    img.area_cm2, img.perimeter_cm = r["area_cm2"], r["perimeter_cm"]
    img.low_confidence, img.manually_corrected = False, True
    db.session.commit()
    refresh_comparisons(img.wound_id)
    return jsonify(img_json(img))


@bp.get("/wounds/<int:wid>/history")
@jwt_required()
def history(wid):
    owned_wound(wid)
    comps = {c.curr_image_id: c for c in Comparison.query.filter_by(wound_id=wid)}
    out = []
    for i in sorted_images(wid):
        d = img_json(i)
        c = comps.get(i.id)
        d["comparison"] = None if not c else dict(
            pct_change=c.pct_change, aligned=c.aligned,
            healed_px=c.healed_px, grown_px=c.grown_px, diff=f"/files/{c.diff_path}")
        out.append(d)
    return jsonify(out)


@bp.get("/wounds/<int:wid>/report.pdf")
@jwt_required()
def report(wid):
    from report import build_report
    w = owned_wound(wid)
    comps = {c.curr_image_id: c for c in Comparison.query.filter_by(wound_id=wid)}
    return send_file(build_report(w, sorted_images(wid), comps, root()),
                     mimetype="application/pdf", download_name=f"smartheal_wound_{wid}.pdf")
