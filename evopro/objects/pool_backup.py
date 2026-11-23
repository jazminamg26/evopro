import random

from evopro.objects.sequence import DesignSeq

class Pool:

    def __init__(self, conf, desseq):
        self.size = conf.flags.pool_sizes[0] 
        # if conf.flags.pool_sizes else 20 #if statement is MH janky fix, but it works
        self.pool = [desseq]
        self.data = {str(desseq)}
        self.seqs_per_iteration = []
        # Keep a reference to the original seed design so that we can rebuild the pool
        # from scratch when running non-evolutionary baselines (e.g., random search).
        self._seed_template = desseq
        self._seed_sequence = str(desseq)
        if conf.flags.starting_seqs_file is not None:
            self._from_starting_seqs_file(desseq, conf.flags.starting_seqs_file)
        
        if len(self.pool) > self.size:
            print("Warning: pool size is smaller than starting sequences file. Truncating pool to size.", len(self.pool), self.size)
            self.pool = self.pool[:self.size]
        while len(self.pool) < self.size:
            newobj = desseq.mutate(self, conf, 1, seq_pred_mode="random")
            self.add(newobj)
        
    def __str__(self):
        strings = []
        for seq in self.pool:
            strings.append(str(seq))
        strings.insert(0, "\nPool size: " + str(len(self.pool)) + "\n~~~~~~~~~~~~~~~~~~~~~~~~~")
        strings.append("~~~~~~~~~~~~~~~~~~~~~~~~~\n")
        return "\n".join(strings)
    
    def _from_starting_seqs_file(self, desseq, filename): 
        seqs = []
        pool = []
        with open(filename, "r") as inpf:
            for l in inpf:
                seqs.append(l.strip().split(","))
        for seq in seqs:
            newseq = ",".join(seq)
            newseqobj = DesignSeq(template_desseq=desseq, sequence=newseq)
            self.add(newseqobj)
                
    def add(self, newseq):
        if newseq and str(newseq) not in self.data:
            self.pool.append(newseq)
            self.data.add(str(newseq))

    def purge(self):
        purge_size = int(self.size/2)            
        if len(self.pool) > purge_size:
            self.sort_by_score()
            self.pool = self.pool[:purge_size]
            self.data = {str(seq) for seq in self.pool}
        

    def rebuild_random(self, conf, curr_iter, sequence_registry):
        """
        Reinitialise the pool with fresh random samples when running a random-search baseline.
        Keeps the seed template for reference but discards evolutionary history between iterations.
        """
        self.pool = []
        self.data = set()

        base_seq = DesignSeq(template_desseq=self._seed_template, sequence=self._seed_sequence)
        base_str = str(base_seq)
        if base_str in sequence_registry:
            base_seq = sequence_registry[base_str]
        else:
            sequence_registry[base_str] = base_seq
        self.pool.append(base_seq)
        self.data.add(base_str)

        while len(self.pool) < self.size:
            parent = random.choice(self.pool)
            newobj = parent.mutate(self, conf, curr_iter, seq_pred_mode="random")
            seq_str = str(newobj)

            if seq_str in sequence_registry:
                newobj = sequence_registry[seq_str]
            else:
                sequence_registry[seq_str] = newobj

            if seq_str not in self.data:
                self.add(newobj)

    # def refill(self, conf, curr_iter, sequence_registry, seq_pred="mpnn"):
    #     i=0
    #     # <MODIFIED>
    #     mutation_rate = conf.flags.mutation_rate
    #     if mutation_rate > 1: #convert to decimal
    #         mutation_rate = mutation_rate/100.0
    #     crossover_percent = conf.flags.crossover_percent
    #     if crossover_percent > 1: #convert to decimal
    #         crossover_percent = crossover_percent/100.0
    #     # </MODIFIED>
    #     while len(self.pool) < self.size:
    #         desseq = random.choice(self.pool)
    #         if seq_pred == "mpnn":
    #             print("DEBUG: Generating sequence via MPNN")
    #             newobj = desseq.mutate(self, conf, curr_iter, seq_pred_mode="mpnn")
    #         else:
    #             will_crossover = False
    #             will_mutate = False
    #             if curr_iter > 1:
    #                 if conf.flags.mode in {"crossover", "both"}:
    #                     if random.random() < crossover_percent or conf.flags.mode == "crossover":
    #                         will_crossover = True
    #                 if conf.flags.mode == "both":
    #                     if random.random() < mutation_rate:
    #                         will_mutate = True
    #             performed_op = False
    #             newobj = desseq
    #             if will_crossover:
    #                 print("DEBUG: Crossing sequence")
    #                 newobj = desseq.mutate(self, conf, curr_iter, seq_pred_mode="crossover")
    #                 performed_op = True
    #             if will_mutate or conf.flags.mode == "mutation":
    #                 print("DEBUG: Mutating sequence")
    #                 newobj = desseq.mutate(self, conf, curr_iter, seq_pred_mode="random")
    #                 performed_op = True
    #             if not performed_op:
    #                 print("DEBUG: Cloning parent (no crossover/mutation applied)")
    #                 newobj = DesignSeq(template_desseq=desseq, sequence=str(desseq))
            
    #         seq_str = str(newobj)

    #         # Use existing object if it's already in the registry
    #         if seq_str in sequence_registry:
    #             newobj = sequence_registry[seq_str]
    #         else:
    #             sequence_registry[seq_str] = newobj

    #         # Avoid duplicates in current pool
    #         if seq_str not in self.data:
    #             self.add(newobj)
    #             self.data.add(seq_str)
    #         i+=1
    #         if i>100:
    #             print("Warning: no new sequences generated by " + seq_pred + ". Defaulting to random.")
    #             newobj = desseq.mutate(self, conf, curr_iter, seq_pred_mode="random")
    #             self.add(newobj)
    #             self.data.add(str(newobj))

    def refill(self, conf, curr_iter, sequence_registry, seq_pred="mpnn"):
        i=0
        crossover_percent = conf.flags.crossover_percent
        if crossover_percent > 1: #convert to decimal
            crossover_percent = crossover_percent/100.0
        if curr_iter >1:
            if seq_pred == "random":
                #X percent of the time, change sequence prediction mode to crossover
                if random.random() < crossover_percent:
                    seq_pred = "crossover"
        while len(self.pool) < self.size:
            desseq = random.choice(self.pool)
            newobj = desseq.mutate(self, conf, curr_iter, seq_pred_mode=seq_pred)
            seq_str = str(newobj)

            # Use existing object if it's already in the registry
            if seq_str in sequence_registry:
                newobj = sequence_registry[seq_str]
            else:
                sequence_registry[seq_str] = newobj

            # Avoid duplicates in current pool
            if seq_str not in self.data:
                self.add(newobj)
                self.data.add(seq_str)
            i+=1
            if i>100:
                print("Warning: no new sequences generated by " + seq_pred + ". Defaulting to random.")
                newobj = desseq.mutate(self, conf, curr_iter, seq_pred_mode="random")
                self.add(newobj)
                self.data.add(str(newobj))

            
    def sort_by_score(self):
        seqs_and_scores = []
        for seq in self.pool:
            seqs_and_scores.append((seq, seq.get_average_score()))
        sorted_seqs_and_scores = sorted(seqs_and_scores, key=lambda x: x[1])
        
        new_pool = []
        for s in sorted_seqs_and_scores:
            new_pool.append(s[0])
        
        self.pool = new_pool
        self.seqs_per_iteration.append(sorted_seqs_and_scores)
        
    def log_scores(self, csv_file, iter, labels=None):
        with open(csv_file, "a") as outf:
            outf.write("\nIteration " + str(iter) + "\t" + labels + "\n")
            for seq in self.pool:
                string = str(seq) + "," + str(seq.get_average_score()) 
                for s in seq.score:
                    string += " | "
                    for elem in s[0]:
                        if type(elem) == tuple:
                            string += "," + str(elem[0]) + "," + str(elem[0]*elem[1])
                outf.write(string + "\n")