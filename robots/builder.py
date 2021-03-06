from helpers import helpers
from robots.movable import Movable
import construction, math, operator, pdb, random, sys,variables

class Builder(Movable):
  def __init__(self,name,structure,location,program):
    super(Builder,self).__init__(name,structure,location,program)
    # The number of beams the robot is carrying
    self.num_beams = variables.beam_capacity

    # Whether or not we should start construction
    self.start_construction = False

    # Set the right weight
    self.weight = (variables.robot_load + variables.beam_load * 
      variables.beam_capacity)

    # Stores variables for construction algorithm (this is the robots memory)
    self.memory = {}

    # Climbing up or down
    self.memory['pos_z'] = None
    self.memory['dir_priority'] = [0]

    # Starting defaults
    self.memory['built'] = False

    # Keeps track of the direction we last moved in.
    self.memory['previous_direction'] = None

    # Stores information on beams that need repairing
    self.memory['broken'] = []

    # Stores whether or not we are constructing vertically or at an angle (for 
    # support)
    self.memory['construct_support'] = False

    # This is the direction towards which the robot looks when searching for a 
    # support tube.
    # This is in the form (x,y,z)
    self.memory['preferred_direction'] = None

    # Modes for supporting structure
    self.search_mode = False
    self.repair_mode = False

  def at_joint(self):
    '''
    Returns whether or not the robot is at a joint
    '''
    if self.on_structure():

      for joint in self.beam.joints:
        # If we're at a joint to another beam
        if helpers.compare(helpers.distance(self.location,joint),0):
          return True

    return False

  def current_state(self):
    state = super(Builder, self).current_state()

    # Copy the memory so that it is not modified
    memory = self.memory.copy()

    # We want the name of the broken beam (more user-friendly)
    memory['broken'] = [(beam.name,beam.endpoints, moment) for beam,moment in memory['broken']]
    state.update({  'num_beams'           : self.num_beams,
                    'start_construction'  : self.start_construction,
                    'memory'              : memory,
                    'repair_mode'         : self.repair_mode,
                    'search_mode'         : self.search_mode})
    
    return state

  def climb_off(self,loc):
    '''
    Returns whether or not the robot should climb off the structure. Additionally,
    sets some special variables
    '''
    # On the xy-plane with no beams OR repairing
    if helpers.compare(loc[2],0) and (self.num_beams == 0 or self.search_mode):
      
      # Not repairing, so calculate direction
      if not self.search_mode:
        direction = helpers.make_vector(self.location,construction.home)
        direction = (direction[0],direction[1],0)
        self.ground_direction = direction

      return True
    
    else:

      # Resetting to None if not in search_mode
      self.ground_direction = (None if not self.search_mode else 
        self.ground_direction)

      return False

  def pickup_beams(self,num = variables.beam_capacity):
    '''
    Pickup beams by adding weight to the robot and by adding num to number 
    carried
    '''
    self.num_beams = self.num_beams + num
    self.weight = self.weight + variables.beam_load * num

    # Set the direction towards the structure
    self.ground_direction = helpers.make_vector(self.location,
      construction.construction_location_center)

  def discard_beams(self,num = 1):
    '''
    Get rid of the specified number of beams by decresing the weight and the 
    number carried
    '''
    self.num_beams = self.num_beams - num
    self.weight = self.weight - variables.beam_load * num

  def at_home(self):
    '''
    True if the robot is in the area designated as home (on the ground)
    '''
    return helpers.within(construction.home, construction.home_size,
      self.location)

  def at_site(self):
    '''
    True if the robot is in the area designated as the construction site 
    (on the ground)
    '''
    return helpers.within(construction.construction_location, 
      construction.construction_size, self.location)

  def pre_decision(self):
    '''
    Takes care of resetting appropriate values.
    '''
    # We build almost never.
    self.start_construction = False
    self.step = variables.step_length
    self.memory['broken'] = []

  # Model needs to have been analyzed before calling THIS function
  def decide(self):
    '''
    This functions decides what is going to be done next based on the analysis 
    results of the program. Therefore, this function should be the one that 
    decides whether to construct or move, based on the local conditions
    and then stores that information in the robot. The robot will then act 
    based on that information once the model has been unlocked. 
    '''
    self.pre_decision()

    # If we decide to construct, then we store that fact in a bool so action 
    # knows to wiggle the beam
    if self.construct():
      self.start_construction = True

    # Movement decisions
    else:
      super(Builder,self).decide()

  # Model needs to be unlocked before running this function! 
  def do_action(self):
    '''
    Overwriting the do_action functionality in order to have the robot move up 
    or downward (depending on whether he is carrying a beam or not), and making 
    sure that he gets a chance to build part of the structure if the situation 
    is suitable. This is also to store the decion made based on the analysis 
    results, so that THEN the model can be unlocked and changed.
    '''
    # Check to see if the robot decided to construct based on analysys results
    if self.start_construction:
      if not self.build():
        print("Could not build...")
      self.start_construction = False

    # Move around
    else:
      super(Builder,self).do_action()

  def remove_specific(self,dirs):
    '''
    In case we ever need to remove a specific direction for the set of available
    directions
    '''
    return dirs

  def preferred(self,vector):
    '''
    Returns True if vector is preferred, False if it is not
    '''
    xy = self.memory['preferred_direction']
    xy = (xy[0],xy[1],0) 
    if (helpers.compare_tuple(xy,(0,0,0)) or helpers.compare_tuple((
      vector[0],vector[1],0),(0,0,0))):
      return True

    return (helpers.smallest_angle((vector[0],vector[1],0),xy) <= 
      construction.beam['direction_tolerance_angle'])

  def filter_dict(self,dirs,new_dirs,comp_functions,preferenced,priorities=[]):
    '''
    Filters a dictinary of directions, taking out all directions not in the 
    correct directions based on the list of comp_functions (x,y,z).

    Edit: Now also filters on priority. If a direction has priority of 0, then
    it MUST be in that direction. The only way that it will ever return an empty
    dictionary is if none of the directions match the direction we want to move
    in for each coordinate with priority zero. Otherwise, we match as many low
    priorty numbers as possible. Same priorities must be matched at the same
    level. 

    Edit: Have done mostly away with priorities, though for compatibility, we
    still keep them in case we want to use them later. Will probably work on 
    removing them entirely. 

    Now, we have added a "preferenced" bool which checks to see if the direction
    is within a specified angle of preferred travel (the angle is dictated in 
    construction.py). The preference is set to True when we are searching for a
    support, otherwise to False. We want this direction, but if we can't find it,
    we reset the variable to False
    '''
    # Access items
    for beam, vectors in dirs.items():

      true_beam = self.structure.get_beam(beam,self.location)

      # If the beam won't be a support beam, pass it..
      if (preferenced and true_beam.endpoints.j in true_beam.joints and 
        self.memory['preferred_direction'] is not None):
        pass 

      # Access each directions
      for vector in vectors:
        coord_bool = True

        # Apply each function to the correct coordinates
        for function, coord in zip(comp_functions,vector):
          coord_bool = coord_bool and function(coord)

        # Additionally, check the x-y direction if we have a preferenced direction
        if (preferenced and self.memory['preferred_direction'] is not None and
          not helpers.is_vertical(vector)):
          coord_bool = coord_bool and self.filter_preferred(vector)

        # Check to see if the direciton is acceptable and keep if it is
        if coord_bool:
          if beam not in new_dirs:
            new_dirs[beam] = [vector]
          else:
            new_dirs[beam].append(vector)

    # Special rules for travelling
    new_dirs = self.remove_specific(new_dirs)

    # Case is not matched, so obtain keys of max values and remove those
    # restraints if the value is not 0
    if new_dirs == {}:

      # We didn't take priorities into account, now we do
      if priorities == []:

        # COPY the LIST
        priorities = list(self.memory['dir_priority'])
      
      max_val = max(priorities)

      # Set to -1 so we don't use them next time, and set comp_funs to True
      for i, val in enumerate(priorities):
        if val == max_val:
          priorities[i] = -1
          comp_functions[i] = lambda a : True

      # We ran out of priorities and we have no preference, so just return the
      # empty set
      if max_val <= 0 and not preferenced:
        return new_dirs

      # We have preference, and/or priorites
      else:
        return self.filter_dict(dirs,new_dirs,comp_functions,False,priorities)

    # Non-empty set
    else:
      return new_dirs

  def filter_directions(self,dirs):
    '''
    Filters the available directions and returns those that move us in the 
    desired direction. Should be overwritten to provide more robost 
    functionality.
    '''
    directions = {}
    base = [lambda x : True, lambda y : True]

    # Still have beams, so move upwards
    if self.num_beams > 0:
      directions = self.filter_dict(dirs, directions,
        (base.append(lambda z : z > 0)),preferenced=self.search_mode)

    # No more beams, so move downwards
    else:
      directions = self.filter_dict(dirs, directions,
        (base.append(lambda z : z < 0)),preferenced=self.search_mode)

    return directions

  def no_available_direction(self):
    '''
    This specifies what the robot should do if there are no directions available
    for travel. This basically means that no beams are appropriate to climb on.
    We pass here, because we just pick the directio randomly later on.
    '''
    pass

  def random_direction(self,directions):
    '''
    Select a random direction from directions
    '''
    beam_name = random.choice(list(directions.keys()))
    direction = random.choice(directions[beam_name])

    return beam_name, direction

  def pick_direction(self,directions):
    '''
    Functions to pick a new direction once it is determined that we either have 
    no previous direction, we are at a joint, or the previous direction is 
    unacceptable)
    '''
    direction = self.random_direction(directions)

    # Store direction in memoery
    self.memory['previous_direction'] = direction

    return direction

  def elect_direction(self,directions):
    '''
    Takes the filtered directions and elects the appropriate one. This function
    takes care of continuing in a specific direction whenever possible.
    '''
    def next_dict(item,dictionary):
      '''
      Returns whether or not the value (a direction vector) is found inside of 
      dictionary (ie, looks for parallel directions)
      '''
      key, value = item
      temp = {}
      for test_key,test_values in dictionary.items():

        # Keys are the same, vectors are parallel (point in same dir too)
        if key == test_key:
          for test_value in test_values:
            if (helpers.parallel(value,test_value) and 
              helpers.dot(value,test_value) > 0):
              if test_key in temp:
                temp[test_key].append(test_value)
              else:
                temp[test_key] = [test_value]
      
      # No values are parallel, so return None
      if temp == {}:
        return None

      # Pick a direction from those that are parallel (so we continue moving)
      # in our preferred direction
      else:
        return self.pick_direction(temp)

    # We are not at a joint and we have a previous direction - keep direction
    if not self.at_joint() and self.memory['previous_direction'] is not None:

      # Pull a direction parallel to our current from the set of directions
      direction_info = next_dict(self.memory['previous_direction'],directions)

      if direction_info is not None:
        return direction_info

    # If we get to this point, either we are at a joint, we don't have a 
    # previous direction, or that previous direction is no longer acceptable
    return self.pick_direction(directions)

  def get_moment_magnitudes(self,name,pivot = None):
    '''
    Returns the moment magnitudes (m11,m22,m33) for the local axes u1,u2,u3 at
    the output station closest to the pivot. If there is no pivot, it returns
    the values from the output station closest to the robot's location.
    '''
    # So we can modify the pivot whenever we call the fuction
    pivot = self.location if pivot is None else pivot

    # Format (ret[0], number_results[1], obj_names[2], i_end distances[3], 
    # elm_names[4], elm_dist[5], load_cases[6], step_types[7], step_nums[8],
    # Ps[9], V2s[10], V3s[11], Ts[12], M2s[13], M3s[14]
    results = self.model.Results.FrameForce(name,0)
    if results[0] != 0:
      # pdb.set_trace()
      helpers.check(results[0],self,"getting frame forces",results=results,
        state=self.current_state())
      return 0

    # Find index of closest data_point
    close_index, i = 0, 0
    shortest_distance = None
    distances = results[3]
    for i_distance in distances:

      # Get beam endpoints to calculate global position of moment
      i_end,j_end = self.structure.get_endpoints(name,self.location)
      beam_direction = helpers.make_unit(helpers.make_vector(i_end,j_end))
      point = helpers.sum_vectors(i_end,helpers.scale(i_distance,
        beam_direction))
      distance = helpers.distance(pivot,point)

      # If closer than the current closes point, update information
      if shortest_distance is None or distance < shortest_distance:
        close_index = i
        shortest_distance = distance

      i += 1

    # Make sure index is indexable
    assert close_index < results[1]

    # Now that we have the closest moment, calculate sqrt(m2^2+m3^2)
    m11 = results[12][close_index]
    m22 = results[13][close_index]
    m33 = results[14][close_index]

    return m11,m22,m33

  def get_moment(self,name):
    '''
    Returns the moment for the beam specified by name at the point closest 
    to the robot itself
    '''
    m11,m22,m33 = self.get_moment_magnitudes(name)

    # Find magnitude
    total = math.sqrt(m22**2 + m33**2)

    return total

  def joint_check(self,name):
    moment = self.get_moment(name)
    return moment < construction.beam['joint_limit']

  def beam_check(self,name):
    moment = self.get_moment(name)
    return moment < construction.beam['beam_limit']

  def filter_feasable(self,dirs):
    '''
    Filters the set of dirs passed in to check that the beam can support a robot
    + beam load if the robot were to walk in the specified direction to the
    very tip of the beam.
    This function is only ever called if an analysis model exists.

    Additionally, this function stores information on the beams that need to be 
    repaired. This is stored in self.memory['broken'], which is originally set
    to none.
    '''
    # Sanity check
    assert self.model.GetModelIsLocked()

    results = {}
    # If at a joint, cycle through possible directions and check that the beams
    # meet the joint_limit. If they do, keep them. If not, discard them.
    if self.at_joint():
      
      # Cycle through directions
      for name, directions in dirs.items():

        # If the name is our beam and we can read moment from beams, 
        # do a structural check instead of a joint check
        if (variables.read_beam and 
          ((self.beam.name == name and self.beam_check(name)) or 
          (self.beam.name != name and self.joint_check(name)))):
          results[name] = directions

        # Otherwise, do a joint_check for all beams
        elif self.joint_check(name):
          results[name] = directions

        # It joint check failed, only keep down directions
        else:

          # Keep only the directions that take us down
          new_directions = ([direction for direction in directions if 
            helpers.compare(direction[2],0) or direction[2] < 0])
          if len(new_directions) > 0:
            results[name] = new_directions

          # Add beam to broken
          beam = self.structure.get_beam(name,self.location)
          if not any(beam in broken for broken in self.memory['broken']):
            moment = self.get_moment(name)
            self.memory['broken'].append((beam,moment))


    # Not at joint, and can read beam moments
    elif variables.read_beam:

      # Sanity check (there should only be one beam in the set of directions if
      # We are not at a joint)
      assert len(dirs) == 1

      # Check beam
      if self.beam_check(self.beam.name):
        results = dirs

      # Add the beam to the broken
      else:

        # Keep only the directions that take us down
        for name,directions in dirs.items():
          new_directions = ([direction for direction in directions if 
            helpers.compare(direction[2],0) or direction[2] < 0])
          if len(new_directions) > 0:
            results[name] = new_directions

        # Beam is not already in broken
        if not any(self.beam in broken for broken in self.memory['broken']):
          moment = self.get_moment(name)
          self.memory['broken'].append((self.beam,moment))

    # We aren't reading beams, so we keep all the directions if not at a joint
    else:
      results = dirs

    return results

  def get_direction(self):
    ''' 
    Figures out which direction to move in. This means that if the robot is 
    carrying a beam, it wants to move upwards. If it is not, it wants to move 
    downwards. So basically the direction is picked by filtering by the 
    z-component
    '''
    # Get all the possible directions, as normal
    info = self.get_directions_info()

    # Filter out directions which are unfeasable if we have an analysis result
    # available
    if self.model.GetModelIsLocked():
      feasable_directions = self.filter_feasable(info['directions'])
    else:
      feasable_directions = info['directions']

    # Now filter on based where you want to go
    directions = self.filter_directions(feasable_directions)

    # This will only occur if no direction takes us where we want to go. If 
    # that's the case, then just a pick a random direction to go on and run the
    # routine for when no directions are available.
    if directions == {}:

      # No direction takes us exactly in the way we want to go, so check if we
      # might need to construct up or might want to repair
      self.no_available_direction()

      # Feasable is empty when our own beam is the one that doesn't support us
      if feasable_directions != {}:
        beam_name, direction = self.elect_direction(feasable_directions)

      # Refilter original directions (to travel down)
      else:
        directions = self.filter_directions(info['directions'])

        # We are on the structure
        if directions != {}:
          beam_name,direction = self.elect_direction(self.filter_directions(
            info['directions']))

        # This happens when we are climbing off the structure
        else:
          beam_name, direction = self.elect_direction(info['directions'])

    # Otherwise we do have a set of directions taking us in the right place, so 
    # randomly pick any of them. We will change this later based on the analysis
    else:
      beam_name, direction = self.elect_direction(directions)

    return {  'beam'      : info['box'][beam_name],
              'direction' : direction }

  def wander(self):
    '''    
    When a robot is not on a structure, it wanders. The wandering in the working
    class works as follows. The robot moves around randomly with the following 
    restrictions:
      The robot moves towards the home location if it has no beams and 
        the home location is detected nearby.
      Otherwise, if it has beams for construction, it moves toward the base 
      specified construction site. If it finds another beam nearby, it has a 
      tendency to climb that beam instead.
    '''
    # Check to see if robot is at home location and has no beams
    if self.at_home() and self.num_beams == 0:
      self.pickup_beams()

    # If we have no beams, set the ground direction to home (TEMP CODE)
    if self.num_beams == 0:
      vector = helpers.make_vector(self.location,construction.home_center)
      self.ground_direction = (vector if not helpers.compare(helpers.length(
        vector),0) else self.non_zero_xydirection())

    # Find nearby beams to climb on
    result = self.ground()

    # Either there are no nearby beams, we are on repair_mode/search_mode, our beams are 0, or
    # we are constructing a support - so don't mess with direction
    if (result == None or self.repair_mode or self.search_mode or 
      self.num_beams == 0 or self.memory['construct_support']):
      direction = self.get_ground_direction()
      new_location = helpers.sum_vectors(self.location,helpers.scale(self.step,
        helpers.make_unit(direction)))
      self.change_location_local(new_location)

    # Nearby beam, jump on it
    else:
      dist, close_beam, direction = (result['distance'], result['beam'],
        result['direction'])
      # If the beam is within steping distance, just jump on it
      if self.num_beams > 0 and dist <= self.step:
        # Set the ground direction to None (so we walk randomly if we do get off
        # the beam again)
        self.ground_direction = None

        # Then move on the beam
        self.move(direction, close_beam)

      # If we can "detect" a beam, change the ground direction to approach it
      elif self.num_beams > 0 and dist <= variables.local_radius:
        self.ground_direction = direction
        new_location = helpers.sum_vectors(self.location, helpers.scale(
          self.step,helpers.make_unit(direction)))
        self.change_location_local(new_location)
      
      # Local beams, but could not detect (this is redundant)
      else:
        direction = self.get_ground_direction()
        new_location = helpers.sum_vectors(self.location,helpers.scale(
          self.step,helpers.make_unit(direction)))
        self.change_location_local(new_location)

  def addbeam(self,p1,p2):
    '''
    Adds the beam to the SAP program and to the Python Structure. Might have to 
    add joints for the intersections here in the future too. Removes the beam 
    from the robot.
    '''
    def addpoint(p): 
      '''
      Adds a point object to our model. The object is retrained in all 
      directions if on the ground (including rotational and translational 
      motion. Returns the name of the added point.
      '''
      # Add to SAP Program
      name = self.program.point_objects.addcartesian(p)
      # Check Coordinates
      if helpers.compare(p[2], 0):
        DOF = (True,True,True,True,True,True)
        if self.program.point_objects.restraint(name,DOF):
          return name
        else:
          print("Something went wrong adding ground point {}.".format(str(p)))
      else:
        return name

    # Unlock the program if necessary
    if self.model.GetModelIsLocked():
      self.model.SetModelIsLocked(False)

    # Add points to SAP Program
    p1_name, p2_name = addpoint(p1), addpoint(p2)
    name = self.program.frame_objects.add(p1_name,p2_name,
      propName=variables.frame_property_name)

    # Skip addition of beam
    if name == '':
      # Set to false if we were constructing support
      self.memory['construct_support'] = False
      return False

    # Set the output statios
    ret = self.model.FrameObj.SetOutputStations(name,2,1,10,False,False)
    if ret != 0:
      print("Could not set output stations for added beam.")
      return False

    # Get rid of one beam
    self.discard_beams()

    # Set to false if we were constructing support
    self.memory['construct_support'] = False

    # Successfully added at least one box
    if self.structure.add_beam(p1,p1_name,p2,p2_name,name) > 0:
      
      # Check to make sure the added element is near us 
      box = self.structure.get_box(self.location)
      try:
        beam = box[name]
      except IndexError:
        print("Failed in addbeam. Adding beam {} at points {} and {} didn't \
          work.".format(name,str(p1),str(p2)))
        return False

      # Cycle through the joints and add the necessary points
      for coord in beam.joints:
        if coord != p1 and coord != p2:
          added = addpoint(coord)
          if added == '':
            print("Something went wrong when adding joint {} to SAP".format(str(
              coord)))
            return False

      return True

    else:
      print("Did not add beam to structure.")
      return False

  def get_angle(self,string):
    '''
    Returns the appropriate ratios for support beam construction
    '''
    angle = construction.beam[string]
    return angle

  def get_angles(self,support = True):
    if support:
      mini,maxi = (self.get_angle('support_angle_min'), self.get_angle(
        'support_angle_max'))
    else:
      mini,maxi = (self.get_angle('min_angle_constraint'), self.get_angle(
        'max_angle_constraint'))

    return mini,maxi

  def non_zero_xydirection(self):
    '''
    Returns a non_zero list of random floats with zero z component.
    The direction returned is a unit vector.
    '''
    # Random list
    tuple_list = ([random.uniform(-1,1),random.uniform(-1,1),
      random.uniform(-1,1)])

    # All are non-zero
    if all(tuple_list):
      tuple_list[2] = 0
      return helpers.make_unit(tuple(tuple_list))

    # All are zero - try again
    else:
      return self.non_zero_xydirection()

  def get_repair_beam_direction(self):
    '''
    Returns the xy direction at which the support beam should be set (if none is
    found). Currently, we just add a bit of disturbace while remaining within 
    the range that the robot was set to search.
    '''
    direction = self.memory['preferred_direction']

    # No preferred direction, so beam was vertically above use
    if xy is None:
      return None

    # Add a bit of disturbace
    else:

      # Project onto xy_plane and make_unit
      xy = helpers.make_unit((direction[0],direction[1],0))
      xy_perp = (-1 * xy[1],xy[0],0)

      # Obtain disturbance based on "search_angle"
      limit = helpers.ratio(construction.beam['direction_tolerance_angle'])
      scale = random.uniform(-1 * limit,limit)
      disturbance = helpers.scale(scale,xy_perp)

      return helpers.sum_vectors(disturbance,xy)

  def support_xy_direction(self):
    '''
    Returns the direction in which the support beam should be constructed
    '''
    # Check to see if direction is vertical
    default_direction = self.get_repair_beam_direction()

    # The beam was vertical
    if default_direction is None:
      xy_dir = self.non_zero_xydirection()

    # Use the default direction
    else:
      xy_dir = default_direction

    return helpers.make_unit(xy_dir)

  def support_vertical_change(self,angle=None):
    '''
    Returns the vertical change for the support endpoint locations
    '''
    # Add beam_directions plus vertical change based on angle ratio (tan)
    if angle is None:
      ratio = helpers.ratio(self.get_angle('support_angle'))

    # We changed the angle from the default  
    else:
      ratio = helpers.ratio(angle)

    # Calculate vertical based on assumption that xy-dir is unit
    vertical = helpers.scale(1/ratio,(0,0,1)) if ratio != 0 else None

    return vertical

  def support_beam_endpoint(self):
    '''
    Returns the endpoint for construction of a support beam
    '''
    # Add beam_directions plus vertical change based on angle ratio (tan)
    ratio = helpers.ratio(self.get_angle('support_angle'))
    vertical = self.support_vertical_change()
    xy_dir = self.support_xy_direction()

    if xy_dir is None or vertical is None:
      direction = (0,0,1)
    else:
      xy_dir = helpers.make_unit(xy_dir)
      direction = helpers.make_unit(helpers.sum_vectors(xy_dir,vertical))

    # Calculate endpoints
    endpoint = helpers.sum_vectors(self.location,helpers.scale(
      construction.beam['length'],direction))

    return endpoint

  def local_angles(self,pivot,endpoint):
    '''
    Calculates the ratios of a beam if it were to intersect nearby beams. 
    Utilizes the line defined by pivot -> endpoint as the base for the ratios 
    '''
    # We place it here in order to have access to the pivot and to the vertical 
    # point

    def add_angles(box,dictionary):
      for name, beam in box.items():

        # Ignore the beam you're on.
        if self.beam == None or self.beam.name != name:

          # Base vector (from which angles are measured)
          base_vector = helpers.make_vector(pivot,endpoint)

          # Get the closest points between the beam we want to construct and the
          # current beam
          points = helpers.closest_points(beam.endpoints,(pivot,endpoint))
          if points != None:

            # Endpoints (e1 is on a vertical beam, e2 is on the tilted one)
            e1,e2 = points

            # If we can actually reach the second point from vertical
            if (not helpers.compare(helpers.distance(pivot,e2),0) and 
              helpers.distance(pivot,e2) <= variables.beam_length):

              # Distance between the two endpoints
              dist = helpers.distance(e1,e2)

              # Vector of beam we want to construct and angle from base_vector
              construction_vector = helpers.make_vector(pivot,e2)
              angle = helpers.smallest_angle(base_vector,construction_vector)

              # Add to dictionary
              if e2 in dictionary:
                assert helpers.compare(dictionary[e2],angle)
              else:
                dictionary[e2] = angle

          # Get the points at which the beam intersects the sphere created by 
          # the vertical beam      
          sphere_points = helpers.sphere_intersection(beam.endpoints,pivot,
            variables.beam_length)
          if sphere_points != None:

            # Cycle through intersection points (really, should be two, though 
            # it is possible for it to be one, in
            # which case, we would have already taken care of this). Either way,
            # we just cycle
            for point in sphere_points:

              # Vector to the beam we want to construct
              construction_vector = helpers.make_vector(pivot,point)
              angle = helpers.smallest_angle(base_vector,construction_vector)

              # Add to dictionary
              if point in dictionary:
                assert helpers.compare(dictionary[point],angle)
              else:
                dictionary[point] = angle

          # Endpoints are also included
          for e in beam.endpoints:
            v = helpers.make_vector(pivot,e)
            l = helpers.length(v)
            if (e not in dictionary and not helpers.compare(l,0) and (
              helpers.compare(l,variables.beam_length) or l < variables.beam_length)):
              angle = helpers.smallest_angle(base_vector,v)
              dictionary[e] = angle

      return dictionary

    # get all beams nearby (ie, all the beams in the current box and possible 
    # those further above)
    boxes = self.structure.get_boxes(self.location)
    '''
    The dictionary is indexed by the point, and each point is 
    associated with one angle. The angle is measured from the pivot->endpoint
    line passed into the function.
    '''
    angles = {}
    for box in boxes:
      angles = add_angles(box,angles)

    return sorted(angles.items(), key = operator.itemgetter(1))

  def build(self):
    '''
    This functions sets down a beam. This means it "wiggles" it around in the 
    air until it finds a connection (programatically, it just finds the 
    connection which makes the smallest angle). Returns false if something went 
    wrong, true otherwise.
    '''
    def check(i,j):
      '''
      Checks the endpoints and returns two that don't already exist in the 
      structure. If they do already exist, then it returns two endpoints that 
      don't. It does this by changing the j-endpoint. This function also takes 
      into account making sure that the returned value is still within the 
      robot's tendency to build up. (ie, it does not return a beam which would 
      build below the limit angle_constraint)
      '''
      # There is already a beam here, so let's move our current beam slightly to
      # some side
      if not self.structure.available(i,j):

        # Create a small disturbace
        lim = variables.random
        f = random.uniform
        disturbance = (f(-1*lim,lim),f(-1*lim,lim),f(-1*lim,lim))

        # find the new j-point for the beam
        new_j = helpers.beam_endpoint(i,helpers.sum_vectors(j,disturbance))

        return check(i,new_j)

      else:

        # Calculate the actual endpoint of the beam (now that we now direction 
        # vector)
        return (i,helpers.beam_endpoint(i,j))

    # Sanitiy check
    assert (self.num_beams > 0)

    # Default pivot is our location
    pivot = self.location

    if self.beam is not None:

      # Obtain any nearby joints, and insert the i/j-end if needed
      all_joints = [coord for coord in self.beam.joints if not helpers.compare(
        coord[2],0)]
      if self.beam.endpoints.j not in all_joints and not helpers.compare(
        self.beam.endpoints.j[2],0):
        all_joints.append(self.beam.endpoints.j)
      if self.beam.endpoints.i not in all_joints and not helpers.compare(
        self.beam.endpoints.i[2],0):
        all_joints.append(self.beam.endpoints.i)

      # Find the nearest one
      joint_coord, dist = min([(coord, helpers.distance(self.location,coord)) for coord in all_joints], key = lambda t: t[1])
      
      # If the nearest joint is within our error, then use it as the pivot
      if dist <= construction.beam['joint_error']:
        pivot = joint_coord

    # Default vertical endpoint (the ratios are measured from the line created 
    # by pivot -> vertical_endpoint)
    vertical_endpoint = helpers.sum_vectors(pivot,helpers.scale(
      variables.beam_length,
      helpers.make_unit(construction.beam['vertical_dir_set'])))

    # Get the ratios
    sorted_angles = self.local_angles(pivot,vertical_endpoint)

    # Find the most vertical position
    final_coord = self.find_nearby_beam_coord(sorted_angles,pivot)

    # Obtain the default endpoints
    default_endpoint = self.get_default(final_coord,vertical_endpoint)
    i, j = check(pivot, default_endpoint)

    # Sanity check
    assert helpers.compare(helpers.distance(i,j),construction.beam['length'])

    return self.addbeam(i,j)

  def find_nearby_beam_coord(self,sorted_angles,pivot):
    '''
    Returns the coordinate of a nearby, reachable beam which results in the
    angle of construction with the most verticality
    '''
    # Limits
    min_constraining_angle, max_constraining_angle = self.get_angles(False)
    min_support_angle,max_support_angle = self.get_angles()

    # Cycle through the sorted angles until we find the right coordinate to build
    for coord, angle in sorted_angles:

      # If the smallest angle is larger than what we've specified as the limit, 
      # but larger than our tolerence, then build
      if min_constraining_angle <= angle and angle <= max_constraining_angle:
        return coord

    return None

  def support_coordinate(self):
    '''
    Returns whether or not the beam being built should be done so as a support beam.
    '''
    return self.memory['construct_support']

  def struck_coordinate(self):
    '''
    Returns whether the struck coordinate of a nearby beam should be used if found
    '''
    return True

  def get_default(self,angle_coord,vertical_coord):
    '''
    Returns the coordinate onto which the j-point of the beam to construct 
    should lie
    '''
    # pdb.set_trace()
    if self.memory['construct_support']:
      return self.support_beam_endpoint()

    elif angle_coord is not None and self.struck_coordinate():
      return angle_coord

    # Retunr the vertical coordinate
    else:
      # Create disturbance
      disturbance = self.get_disturbance()
      
      # We add a bit of disturbance every once in a while
      new_coord = vertical_coord if self.default_probability() else (
      helpers.sum_vectors(vertical_coord,disturbance))
      return new_coord

  def get_disturbance(self):
    '''
    Returns the disturbance level for adding a new beam at the tip (in this
    class, the disturbance is random at a level set in variables.random)
    '''
    change = variables.random
    return helpers.make_unit((random.uniform(-change,change),
      random.uniform(-change,change),0))

  def default_probability(self):
    '''
    Returns whether or not the disturbance should be applied to the current 
    contruction. Realistically, this should be a probabilistic function.

    True means that the disturbance is NOT applied
    False means that the disturbance is
    '''
    return (random.randint(0,4) == 1)

  def construct(self):
    '''
    Decides whether the local conditions dictate we should build (in which case)
    ''' 
    if ((self.at_site()) and not self.memory['built'] and 
      self.num_beams > 0):
      self.memory['built'] = True
      self.memory['constructed'] += 1
      return True

    else:
      self.memory['built'] = False
      return False
