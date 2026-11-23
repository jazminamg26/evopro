import sys, importlib
from scoring.standard_score_funcs import *
from utils.parsing_utils import *
from utils.parsing import parse_results
from utils.hbonding import score_hydrogen_bonds
from utils.utils import check_omegaconf_key_exists

def score_overall_mod(results, sequences, dsobj, conf):
    # === Setup ===
    all_chains = [x.strip() for x in conf.structure_prediction.structure_pred_chains]
    results, pdbs = parse_results(results, conf)

    # Encabezado: placeholders para secuencias + overall
    num_chains_seq = len(str(dsobj).split(","))
    label_parts = [""] * max(0, num_chains_seq - 1)
    label_parts.append("overall_score")

    # Acumuladores
    components = []    # lista de (nombre_col, valor, peso) por componente
    contributions = [] # lista de (valor * peso)

    def add_component(name, value, weight, per_chain=False, chain_id=None):
        col = name if not per_chain else f"{name}_chain{chain_id}"
        v = float(value)
        w = float(weight)
        components.append((col, v, w))
        contributions.append(v * w)
        # Para el CSV, encabezado con 2 columnas por componente: crudo y ponderado
        label_parts.extend([col, f"weighted_{col}"])

    # === pLDDT ===
    if conf.scoring.plddt.score_plddt:
        plddt_chains  = [x.strip() for x in conf.scoring.plddt.preds.split(",")]
        plddt_weights = parse_weights(conf.scoring.plddt.weights, plddt_chains)
        residues      = get_residues(conf.scoring.plddt.residues, dsobj)
        i = 0
        for result, pred in zip(results, all_chains):
            if pred in plddt_chains:
                if 'plddt' in result:
                    plddt_score = get_avg_plddt(result, reslist=residues)
                else:
                    _, plddt_score = calculate_residue_plddt(result, reslist=residues)
                add_component("pLDDT", plddt_score, plddt_weights[i], per_chain=True, chain_id=pred)
                i += 1

    # === pTM ===
    if conf.scoring.ptm.score_ptm:
        ptm_chains  = [x.strip() for x in conf.scoring.ptm.preds.split(",")]
        ptm_weights = parse_weights(conf.scoring.ptm.weights, ptm_chains)
        i = 0
        for result, pred in zip(results, all_chains):
            if pred in ptm_chains and 'ptm' in result:
                add_component("pTM", float(result['ptm']), ptm_weights[i], per_chain=True, chain_id=pred)
                i += 1

    # === ipTM ===
    if conf.scoring.iptm.score_iptm:
        iptm_chains  = [x.strip() for x in conf.scoring.iptm.preds.split(",")]
        iptm_weights = parse_weights(conf.scoring.iptm.weights, iptm_chains)
        i = 0
        for result, pred in zip(results, all_chains):
            if pred in iptm_chains and 'iptm' in result:
                add_component("ipTM", float(result['iptm']), iptm_weights[i], per_chain=True, chain_id=pred)
                i += 1

    # === Contactos (PAE-weighted) + bonus/penalty ===
    if conf.scoring.contacts.score_contacts:
        contacts_chains  = [x.strip() for x in conf.scoring.contacts.preds.split(",")]
        contacts_weights = parse_weights(conf.scoring.contacts.weights, contacts_chains)
        reslist1 = get_tokens(conf.scoring.contacts.interface_1, dsobj)
        reslist2 = get_tokens(conf.scoring.contacts.interface_2, dsobj)
        bonus_residues   = get_tokens(conf.scoring.contacts.bonus_residues, dsobj) if conf.scoring.contacts.bonus_residues else None
        penalty_residues = get_tokens(conf.scoring.contacts.penalty_residues, dsobj) if conf.scoring.contacts.penalty_residues else None

        i = 0
        for result, seq, pred in zip(results, sequences, all_chains):
            if pred in contacts_chains:
                _, cscore = score_contacts_pae_weighted(result, seq, reslist1, reslist2, conf)
                add_component("ContactScore", cscore, contacts_weights[i], per_chain=True, chain_id=pred)
                i += 1
                if bonus_residues:
                    _, bonus = score_contact(result, bonus_residues, reslist2, dist=conf.scoring.contacts.bonus_distance)
                    add_component("BonusScore", bonus, conf.scoring.contacts.bonus_weight, per_chain=True, chain_id=pred)
                if penalty_residues:
                    _, pen = score_contact(result, penalty_residues, reslist2, dist=conf.scoring.contacts.penalty_distance)
                    add_component("PenaltyScore", pen, conf.scoring.contacts.penalty_weight, per_chain=True, chain_id=pred)

    # === Cambio conformacional (RMSD entre dos predicciones) ===
    if conf.scoring.conf_change.score_conf_change:
        preds = [x.strip() for x in conf.scoring.conf_change.preds.split(",")]
        if len(preds) != 2:
            raise ValueError("conf_change.preds debe tener exactamente dos cadenas (ej. 'AB,A')")
        pred1, pred2 = preds
        pdb1 = pdb2 = None
        for result, pred in zip(results, all_chains):
            if pred == pred1: pdb1 = result['pdb']
            if pred == pred2: pdb2 = result['pdb']
        reslist = get_residues(conf.scoring.conf_change.residues, dsobj)
        conf_diff = score_rmsd(pdb1, pdb2, reslist=reslist)
        add_component("ConfDiffScore", conf_diff, conf.scoring.conf_change.weights)

        # Penalización opcional por umbral
        if hasattr(conf.scoring.conf_change, "threshold_penalty") and conf.scoring.conf_change.threshold_penalty:
            thr = float(conf.scoring.conf_change.threshold)
            k   = float(conf.scoring.conf_change.spring_constant)
            if conf_diff > thr:
                penalty = k * (conf_diff - thr)
                add_component("ConfDiffPenaltyAboveThreshold", penalty, 1.0)

    # === RMSD vs referencia ===
    if conf.scoring.rmsd.score_rmsd:
        rmsd_chains  = [x.strip() for x in conf.scoring.rmsd.preds.split(",")]
        rmsd_weights = parse_weights(conf.scoring.rmsd.weights, rmsd_chains)
        reslist = get_residues(conf.scoring.rmsd.residues, dsobj)
        i = 0
        for result, pred in zip(results, all_chains):
            if pred in rmsd_chains:
                # ¡Ojo! Pasa el PATH del PDB referencia, no el contenido
                r = score_rmsd(result['pdb'], conf.scoring.rmsd.rmsd_pdb, reslist)
                add_component("RMSDScore", r, rmsd_weights[i], per_chain=True, chain_id=pred)
                i += 1

        if hasattr(conf.scoring.rmsd, "threshold_penalty") and conf.scoring.rmsd.threshold_penalty:
            thr = float(conf.scoring.rmsd.threshold)
            k   = float(conf.scoring.rmsd.spring_constant)
            for back in range(1, i+1):
                name, r_value, _w = components[-back]
                if name.startswith("RMSDScore") and r_value > thr:
                    penalty = k * (r_value - thr)
                    add_component("RMSDPenaltyAboveThreshold", penalty, 1.0)

    # === Puentes de H ===
    if check_omegaconf_key_exists("scoring.hbond", conf) and conf.scoring.hbond.score_hbond:
        hbond_chains  = [x.strip() for x in conf.scoring.hbond.preds.split(",")]
        hbond_weights = parse_weights(conf.scoring.hbond.weights, hbond_chains)
        reslist1 = get_tokens(conf.scoring.hbond.interface_1, dsobj)
        reslist2 = get_tokens(conf.scoring.hbond.interface_2, dsobj)
        i = 0
        for result, pred in zip(results, all_chains):
            if pred in hbond_chains:
                _, hscore = score_hydrogen_bonds(result, reslist1, reslist2, max_don_h_dist=conf.scoring.hbond.max_don_h_dist)
                add_component("HBondScore", hscore, hbond_weights[i], per_chain=True, chain_id=pred)
                i += 1

    # === Hidrofobicidad interfaz/superficie ===
    if check_omegaconf_key_exists("scoring.hydrophobic_interface", conf) and conf.scoring.hydrophobic_interface.score_hydrophobic_interface:
        hyd_chains  = [x.strip() for x in conf.scoring.hydrophobic_interface.preds.split(",")]
        hyd_weights = parse_weights(conf.scoring.hydrophobic_interface.weights, hyd_chains)
        i = 0
        for result, pred in zip(results, all_chains):
            if pred in hyd_chains:
                h = score_hydrophobicity(result, conf, score_type="interface")
                add_component("HydrophobicityInterface", h, hyd_weights[i], per_chain=True, chain_id=pred)
                i += 1

    if check_omegaconf_key_exists("scoring.hydrophobic_surface", conf) and conf.scoring.hydrophobic_surface.score_hydrophobic_surface:
        hyd_chains  = [x.strip() for x in conf.scoring.hydrophobic_surface.preds.split(",")]
        hyd_weights = parse_weights(conf.scoring.hydrophobic_surface.weights, hyd_chains)
        i = 0
        for result, pred in zip(results, all_chains):
            if pred in hyd_chains:
                h = score_hydrophobicity(result, conf, score_type="surface")
                add_component("HydrophobicitySurface", h, hyd_weights[i], per_chain=True, chain_id=pred)
                i += 1

    # === Custom ===
    if conf.scoring.custom.score_custom:
        custom_chains  = [x.strip() for x in conf.scoring.custom.preds.split(",")]
        custom_weights = parse_weights(conf.scoring.custom.weights, custom_chains)
        i = 0
        for result, pred in zip(results, all_chains):
            if pred in custom_chains:
                c = score_custom(result, conf, dsobj)
                add_component("CustomScore", c, custom_weights[i], per_chain=True, chain_id=pred)
                i += 1

    # === Ensamble final ===
    overall = float(sum(contributions))
    # Fila: [overall, (valor, peso), (valor, peso), ...]
    score_row = [overall] + [(v, w) for (_name, v, w) in components]
    label = ",".join(label_parts)
    return score_row, pdbs, results, label

def score_custom(result, conf, dsobj):
    try:
        if conf.scoring.custom:
            scorefile = conf.scoring.custom.custom_script.rsplit("/", 1)
            scorepath = scorefile[0]
            scorefilename = scorefile[1].split(".")[0]
            sys.path.append(scorepath)
            mod = importlib.import_module(scorefilename)
            scorefunc = getattr(mod, conf.scoring.custom.custom_score_func)
            return scorefunc(result, conf, dsobj)
    except Exception as e:
        raise ValueError(f"Invalid score function: {e}")

def calc_penalty_score(score, threshold, spring_constant):
    if score > threshold:
        return spring_constant * (score - threshold)
    return 0
