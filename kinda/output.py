from __future__ import absolute_import

def write_pil(KindaSystem, pil, spurious=False, unproductive=False, molarity='M', time='s', prefix=None):
    """Write the KindaSystem object into a proper *.pil format.

    Args:
        KindaSystem (:obj:`kinda.System()`): The kinda.System() object.
        pil (filehandle): Filehandle to write to.
        spurious (bool, optional): Print information about spurious complexes and reactions.
        unproductive (bool, optional): Print information about unproductive complexes and reactions.

    NOTE: Eventually, this function should return more than just the CRN. That 
        means info about domains, complexes, strands (ugh), etc.
    """

    I = 0 # counts number of intermediate species.

    def format_rate_units(rate, arity, molarity, time):
        """ Reaction objects *always* specify rate in /M and /s.
        """
        if time == 's':
            pass
        elif time == 'm':
            rate *= 60
        elif time == 'h':
            rate *= 3600
        else :
            raise NotImplementedError
    
        if molarity == 'M':
            pass
        elif molarity == 'mM':
            if arity[0] > 1:
                factor = arity[0] - 1
                rate /= (factor * 1e3)
        elif molarity == 'uM':
            if arity[0] > 1:
                factor = arity[0] - 1
                rate /= (factor * 1e6)
        elif molarity == 'nM':
            if arity[0] > 1:
                factor = arity[0] - 1
                rate /= (factor * 1e9)
        else :
            raise NotImplementedError
    
        return rate


    pil.write('\n# Condensed reactions\n')
    for rxn in KindaSystem.get_reactions(spurious=spurious, unproductive=unproductive):
        stats = KindaSystem.get_stats(rxn)

        k_1 = stats.get_k1(max_sims=0)
        k_1_err = stats.get_k1_error(max_sims=0)
        k_2 = stats.get_k2(max_sims=0)
        k_2_err = stats.get_k2_error(max_sims=0)

        reactants = map(lambda x:x.name, rxn.reactants)
        products  = map(lambda x:x.name, rxn.products)
        if prefix :
            inter = prefix + str(I)
        else :
            inter = '_'.join(sorted(reactants) + ['to'] + sorted(products))

        if k_1 > 0 and k_2 > 0 :
            pil.write('reaction [k1 = {:12g} +/- {:12g} {:4s}] {} -> {}\n'.format(
                format_rate_units(k_1, (len(reactants), 1), molarity, time), 
                format_rate_units(k_1_err, (len(reactants), 1), molarity, time), 
                '/{}'.format(molarity)*len(reactants)+'/s',
                ' + '.join(reactants), inter))

            pil.write('reaction [k2 = {:12g} +/- {:12g} {:4s}] {} -> {}\n'.format(
                format_rate_units(k_2, (1,len(products)), molarity, time), 
                format_rate_units(k_2_err, (1,len(products)), molarity, time), '/s',
                inter, ' + '.join(products)))
        else :
            pil.write('# reaction [k1 = {:12g} +/- {:12g} {:4s}] {} -> {}\n'.format(
                format_rate_units(k_1, (len(reactants), 1), molarity, time), 
                format_rate_units(k_1_err, (len(reactants), 1), molarity, time), 
                '/{}'.format(molarity)*len(reactants)+'/s',
                ' + '.join(reactants), inter))

            pil.write('# reaction [k2 = {:12g} +/- {:12g} {:4s}] {} -> {}\n'.format(
                format_rate_units(k_2, (1,len(products)), molarity, time), 
                format_rate_units(k_2_err, (1,len(products)), molarity, time), '/s',
                inter, ' + '.join(products)))
        I += 1

    pil.write('\n# Resting macrostate probabilities\n')
    restingsets = KindaSystem.get_restingsets(spurious=spurious)
    for rms in restingsets:
        stats = KindaSystem.get_stats(rms)
    
        p = 1 - stats.get_conformation_prob(None, max_sims=0)
        p_err = stats.get_conformation_prob_error(None, max_sims=0)
        temp_dep = stats.get_temporary_depletion(max_sims=0)

        pil.write('# {:20s} [Prob = {:12g} +/- {:12g}; Depletion = {:12g}]\n'.format(
            rms.name, p, p_err, temp_dep))

    # In a table, print out temporary depletion levels for each pairwise combination of resting sets.
    restingsets = KindaSystem.get_restingsets(spurious=False)
    if unproductive is None:
        pil.write('\n# Temporary depletion details\n')
        for rms1 in restingsets:
            rms_stats = KindaSystem.get_stats(rms1)

            for rms2 in restingsets:
                rxns = KindaSystem.get_reactions(unproductive=True, reactants=[rms1,rms2])
                assert len(rxns) == 1
                rxn_stats = KindaSystem.get_stats(rxns[0])
                depl = rms_stats.get_temporary_depletion_due_to(rxn_stats, max_sims=0)

                pil.write('# {:20s} [Depletion due to {:20s} = {:12g}]\n'.format(
                    rms1.name, rms2.name, depl))


