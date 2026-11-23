
                unsatisfied.append(motif)
        return unsatisfied

    def enforce_motif(self, seq: List[str], motif: Dict[str, Sequence[int]]) -> None:
        pattern = motif["pattern"]
        positions = motif.get("positions")
        if positions:
            start = positions[0]
            for offset, aa in enumerate(pattern):
                idx = start + offset
                if 0 <= idx < len(seq):
                    seq[idx] = aa
        else:
            start = random.randrange(0, len(seq) - len(pattern) + 1)
            for offset, aa in enumerate(pattern):
                seq[start + offset] = aa

    # ------------------------------------------------------------------
    # Scoring components (lower is better)
    # ------------------------------------------------------------------
    def _score_disorder(self, seq: Sequence[str]) -> float:
        count = sum(1 for aa in seq if aa in DISORDER_RESIDUES)
        return count / len(seq)

    def _score_hydrophobic_core(self, seq: Sequence[str]) -> float:
        if not self.config.hydrophobic_regions:
            return 0.0
        penalties = []
        for region in self.config.hydrophobic_regions:
            start = region["start"]
            end = region["end"]
            region_seq = seq[start:end]
            if not region_seq:
                continue
            fraction = sum(1 for aa in region_seq if aa in HYDROPHOBIC_RESIDUES) / len(region_seq)
            penalties.append(1.0 - fraction)
        return float(np.mean(penalties)) if penalties else 0.0

    def _score_charge_balance(self, seq: Sequence[str]) -> float:
        positive = sum(1 for aa in seq if aa in posITIVE_RESIDUES)
        negative = sum(1 for aa in seq if aa in NEGATIVE_RESIDUES)
        net_charge = positive - negative
        return abs(net_charge - self.config.target_charge)

    def _score_motifs(self, seq: Sequence[str]) -> float:
        unsatisfied = self.unsatisfied_motifs(seq)
        return len(unsatisfied) / max(len(self.config.motifs), 1) if self.config.motifs else 0.0

    def evaluate(self, seq: Sequence[str]) -> Dict[str, float]:
        components = {
            "disorder": self._score_disorder(seq),
            "hydrophobic_core": self._score_hydrophobic_core(seq),
            "charge_balance": self._score_charge_balance(seq),
            "motif": self._score_motifs(seq),
        }
        overall = sum(self.weights.get(k, 0.0) * v for k, v in components.items())
        
        components["overall"] = overall
        return components

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_hydrophobic_index_list(self) -> List[int]:
        indices: List[int] = []
        for region in self.config.hydrophobic_regions:
            indices.extend(list(range(region["start"], region["end"])))
        indices = [idx for idx in indices if 0 <= idx < self.config.sequence_length]
        return indices

    def random_hydrophobic_index(self) -> Optional[int]:
        if not self._hydrophobic_indices:
            return None
        return random.choice(self._hydrophobic_indices)

