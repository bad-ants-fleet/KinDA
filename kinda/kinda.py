# kinda.py
# Created by Joseph Berleant, 1/12/2018
#
# Defines the System class, encapsulating statistics calculations for DNA strand-displacement system properties.

## IMPORTS

from .statistics import stats_utils
from .objects import io_PIL
import options
  

## GLOBALS

# Convenience function to create System object from a given PIL file
# Currently only accepts old-style PIL notation (no kernel notation)
def from_pil(path, enumeration = True, **kwargs):
  domains, strands, complexes = io_PIL.from_PIL(path)
  return System(complexes, enumeration = enumeration, **kwargs)


## CLASSES
class System(object):
  """ Stores and manages Stats objects for each system component for easier retrieval.
      Data can also be stored in a file and retrieved for later analysis.
      A System object is instantiated with an EnumerateJob object, from which
      detailed and condensed reactions as well as resting sets and complexes are taken. """

  def __init__(self, complexes, restingsets = [], detailed_reactions = [], condensed_reactions = [], enumeration = True, kinda_params = {}, peppercorn_params = {}, multistrand_params = {}, nupack_params = {}):
    """ Constructs a System object with the given complexes, restingsets, reactions, and condensed reactions.
    If enumeration is True (default), the Peppercorn enumerator is used to enumerate a detailed reaction network.
    System performs reaction condensation to produce the condensed reaction network. The given restingsets and
    reactions are added to the enumerated network. Detailed reactions are added to the network prior to condensation.
    If enumeration is False, then no enumeration is performed and only the given resting sets and reactions are
    used for analysis.
    """

    ## Choose parameters for Peppercorn, Multistrand, and Nupack
    ## GvR doesn't like the idiom  dict(d1, **d2)  but I do
    self._kinda_params = dict(options.kinda_params, **kinda_params)
    self._peppercorn_params = dict(options.peppercorn_params, **peppercorn_params)
    self._multistrand_params = dict(options.multistrand_params, **multistrand_params)
    self._nupack_params = dict(options.nupack_params, **nupack_params)

    # Store given data
    # We extract any resting sets and complexes from higher-order objects to maintain consistency
    self._condensed_reactions = set(condensed_reactions)
    self._detailed_reactions = set(detailed_reactions)
    self._restingsets = set(restingsets
        + [rs for rxn in self._condensed_reactions for rs in rxn.reactants+rxn.products]
    )
    self._complexes = set(complexes
        + [c for rs in self._restingsets for c in rs.complexes]
        + [c for rxn in self._detailed_reactions for c in rxn.reactants+rxn.products]
    )

    if enumeration:
      # Import EnumerateJob only if necessary
      from .enumeration.enumeratejob import EnumerateJob

      # Create enumeration object
      self._enum_job = EnumerateJob(
          complexes = self.complexes,
          reactions = self.detailed_reactions,
          peppercorn_params = self._peppercorn_params
      )

      # Incorporate enumerated data
      self._complexes = set(self._enum_job.get_complexes())
      self._restingsets = set(self._enum_job.get_restingsets())
      self._detailed_reactions = set(self._enum_job.get_reactions())
      self._condensed_reactions = set(self._enum_job.get_restingset_reactions())
    else:
      self._enum_job = None

    # Filter out unimolecular reactions, if these are disabled.
    if not self._kinda_params['enable_unimolecular_reactions']:
      self._condensed_reactions = set(filter(lambda rxn: len(rxn.reactants)==2, self._condensed_reactions))

    # Create stats objects for reactions and resting sets
    # make_stats() will also make stats objects for potential spurious reactions and resting sets
    self._rs_to_stats, self._rxn_to_stats = stats_utils.make_stats(
        list(self._complexes),
        list(self._restingsets),
        list(self._detailed_reactions),
        list(self._condensed_reactions),
        kinda_params = self._kinda_params,
        multistrand_params = self._multistrand_params,
        nupack_params = self._nupack_params
    )

    # Pull out spurious reactions/resting sets
    self._spurious_restingsets = set(self._rs_to_stats.keys()) - self._restingsets
    self._spurious_condensed_reactions = set(self._rxn_to_stats.keys()) - self._condensed_reactions

    # Set default max concentration for each resting set
    for rs_stats in self._rs_to_stats.values():
      rs_stats.c_max = self._kinda_params.get('max_concentration', 1e-7)


  ## Basic get functions for system objects

  @property
  def initialization_params(self):
    """ Returns a dict of the parameters used to initialize this system, including
    those set by the defaults in options.py. """
    return {
      'kinda_params': self._kinda_params.copy(),
      'multistrand_params': self._multistrand_params.copy(),
      'nupack_params': self._nupack_params.copy(),
      'peppercorn_params': self._peppercorn_params.copy()
    }
  @property
  def kinda_params(self):
    """ Returns a dict of the KinDA parameters used when initializing the system.
    Equivalent to initialization_params['kinda_params']. """
    return self._kinda_params.copy()
  @property
  def multistrand_params(self):
    """ Returns a dict of the Multistrand parameters used when initializing the system.
    Equivalent to initialization_params['multistrand_params']. """
    return self._multistrand_params.copy()
  @property
  def nupack_params(self):
    """ Returns a dict of the NUPACK parameters used when initializing the system.
    Equivalent to initialization_params['nupack_params']. """
    return self._nupack_params.copy()
  @property
  def peppercorn_params(self):
    """ Returns a dict of the Peppercorn parameters used when initializing the system.
    Equivalent to the initialization_params['peppercorn_params']. """
    return self._peppercorn_params.copy()

  @property
  def complexes(self):
    """ Returns a list of all complexes (given and enumerated) predicted for the system. """
    return list(self._complexes)

  @property
  def restingsets(self):
    """ Returns a list of all resting sets (given, enumerated, and spurious) predicted for the system. """
    return list(self._restingsets | self._spurious_restingsets)

  @property
  def detailed_reactions(self):
    """ Returns a list of detailed reactions (given and enumerated) predicted for the system. """
    return list(self._detailed_reactions)

  @property
  def condensed_reactions(self):
    """ Returns a list of all resting-set (condensed) reactions (given, enumerated, and spurious) for the system. """
    return list(self._condensed_reactions | self._spurious_condensed_reactions)


  ## Convenience filters for specific objects


  def get_reactions(self, reactants = [], products = [], arity = 2, unproductive = None, spurious = None):
    """ Returns a list of all reactions including the given reactants and the given products.
        If specified, spurious = True will return only spurious reactions (those not enumerated by Peppercorn)
        and spurious = False will return only enumerated reactions. Otherwise, no distinction will be made.
        """
    if spurious == True:
      rxns = list(self._spurious_condensed_reactions)
    elif spurious == False:
      rxns = list(self._condensed_reactions)
    else:
      rxns = list(self._spurious_condensed_reactions | self._condensed_reactions)

    if unproductive == True:
      rxns = filter(lambda x: x.has_reactants(x.products) and x.has_products(x.reactants), rxns)
    elif unproductive == False:
      rxns = filter(lambda x: not(x.has_reactants(x.products) and x.has_products(x.reactants)), rxns)

    if arity is not None:
      rxns = filter(lambda x: len(x.reactants)==arity, rxns)

    return filter(lambda x: x.has_reactants(reactants) and x.has_products(products), rxns)
  def get_reaction(self, **kwargs):
    """ Returns a single reaction matching the criteria given. """
    rxns = self.get_reactions(**kwargs)
    if len(rxns) == 0:
      print "KinDA: ERROR: SystemStats.get_reaction() failed to find a reaction with the given criteria."
      return None
    elif len(rxns) > 1:
      print "KinDA: WARNING: SystemStats.get_reactino() found multiple reactions with the given criteria."

    return rxns[0]

  def get_restingsets(self, complex = None, strands = [], name = None, complex_name = None, spurious = False):
    """ Returns a list of resting sets satisfying the filter arguments.
    If complex is specified, only resting sets with this complex are returned.
    If strands is specified, only resting sets with all given strands are returned.
    If name is specified, only restingsets with this name are returned.
    If complex_name is specified, only resting sets with a complex with this name are returned.
    If spurious is True, only spurious resting sets are returned.
    If spurious is False, only non-spurious resting sets are returned.
    If spurious is None, both spurious and non-spurious resting sets may be returned.
    """
    if spurious == True:
      rs = list(self._spurious_restingsets)
    elif spurious == False:
      rs = list(self._restingsets)
    else:
      rs = list(self._restingsets | self._spurious_restingsets)

    if complex is not None:
      rs = filter(lambda x: complex in x, rs)
    if strands != []:
      rs = filter(lambda x: all([s in x.strands for s in strands]), rs)
    if name is not None:
      rs = filter(lambda x: x.name == name, rs)
    if complex_name is not None:
      rs = filter(lambda x: complex_name in [c.name for c in x.complexes], rs)

    return rs
  def get_restingset(self, complex = None, strands = [], name = None, complex_name = None, spurious = False):
    rs_list = self.get_restingsets(complex = complex, strands = strands, name = name, complex_name = complex_name, spurious = spurious)
    if len(rs_list) == 0:
      print "KinDA: ERROR: SystemStats.get_restingset() failed to find a resting set with the given criteria"
      return None
    elif len(rs_list) > 1:
      print "KinDA: WARNING: SystemStats.get_restingset() found multiple resting sets with the given criteria"
    
    return rs_list[0]

  def get_complexes(self, name = None):
    complexes = list(self._complexes)
    
    if name is not None:
      complexes = filter(lambda x: x.name == name, complexes)

    return complexes
  def get_complex(self, name = None):
    complexes = self.get_complexes(name = name)
    if len(complexes) == 0:
      print "KinDA: ERROR: SystemStats.get_complexes() failed to find a complex with the given criteria."
      return None
    elif len(complexes) > 1:
      print "KinDA: WARNING: SystemStats.get_complexes() found multiple complexes with the given criteria."
    
    return complexes[0]

  def get_stats(self, obj):
    """ Returns the stats object corresponding to the given system object.
    obj must be a resting-set reaction or resting set in the system. """
    if obj in self._rxn_to_stats:
      return self._rxn_to_stats[obj]
    elif obj in self._rs_to_stats:
      return self._rs_to_stats[obj]
    else:
      print "Statistics for object {0} not found.".format(obj)


def import_data(path):
  return stats_utils.import_data(path)
def export_data(sstats, path):
  return stats_utils.export_data(sstats, path)
