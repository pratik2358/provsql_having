# Gap program to look for all commutative m-semirings of small size
LoadPackage("smallsemi");

IsCommutativeSemiring := function(add, mul, zero, one)
  local n, x, y, z;

  n := Length(add);

  # Associativity of times
  for x in [1..n] do
    for y in [1..n] do
      for z in [1..n] do
        if mul[x][ mul[y][z] ] <> mul[ mul[x][y] ][z] then
          return false;
        fi;
      od;
    od;
  od;

  # Commutativity of times
  for x in [1..n] do
    for y in [1..n] do
      if mul[x][y] <> mul[y][x] then
        return false;
      fi;
    od;
  od;

  # Left-distributivity of times
  for x in [1..n] do
    for y in [1..n] do
      for z in [1..n] do
        if mul[x][ add[y][z] ] <> add[ mul[x][y] ][ mul[x][z] ] then
          return false;
        fi;
      od;
    od;
  od;

  # 0 annilihates times
  for x in [1..n] do
    if mul[zero][x] <> zero then
      return false;
    fi;
  od;

  return true;
end;

SemiringsOfSize := function(n)
  local M, allmuls, mul, out, add, zero, one, good,
    commutativeMonoids, x, y, z, le, sub, allsubs;

  out := [];

  # All monoids of size n (Semigroups package)
  commutativeMonoids := AllSmallSemigroups(n, IsCommutative, true,
                                              IsMonoidAsSemigroup, true);

  for M in commutativeMonoids do
    add := MultiplicationTable(M);

    # Find the zero
    zero := fail;
    for x in [1..n] do
      good := true;
      for y in [1..n] do
        if add[x][y] <> y then
          good := false; break;
        fi;
      od;
      if good then zero := x; break; fi;
    od;

    # Should not happen
    if zero = fail then continue; fi;

    allmuls := Cartesian(List([1..n^2], i-> [1..n]));

    for mul in allmuls do
      mul := List([1..n], i -> mul{[(i-1)*n+1 .. i*n]});

      # Look for a one
      one := fail;
      for x in [1..n] do
        good := true;
        for y in [1..n] do
          if mul[x][y] <> y or mul[y][x] <> y then
            good := false; break;
          fi;
        od;
        if good then one := x; break; fi;
      od;
      if one = fail then continue; fi;

      if IsCommutativeSemiring(add, mul, zero, one) then
        # Construct the natural preorder
        le := List([1..n^2]);
        le := List([1..n], i -> le{[(i-1)*n+1 .. i*n]});
        for x in [1..n] do
          for y in [1..n] do
            le[x][y] := false;
            for z in [1..n] do
              if add[x][z] = y then le[x][y] := true; break; fi;
            od;
          od;
        od;

        # Check it is an order, i.e., that it is antisymmetric
        good := true;
        for x in [1..n] do
          for y in [(x+1)..n] do
            if x<>y and le[x][y] and le[y][x] then
              good := false;
              break;
            fi;
          od;
          if not good then break; fi;
        od;
        if not good then continue; fi;

        # Find a sub (if one exists)
        allsubs := Cartesian(List([1..n^2], i-> [1..n]));
        for sub in allsubs do
          sub := List([1..n], i -> sub{[(i-1)*n+1 .. i*n]});
          good := true;
          for x in [1..n] do
            for y in [1..n] do
              for z in [1..n] do
                if le[sub[x][y]][z] <> le[x][add[y][z]] then
                  good := false; break;
                fi;
              od;
              if not good then break; fi;
            od;
            if not good then break; fi;
          od;
          if good then break; fi;
        od;
        if not good then continue; fi;

        Add(out, rec(
          add := add,
          mul := mul,
          zero := zero,
          one:= one,
          le := le,
          sub := sub
        ));
      fi;
    od;
  od;

  return out;
end;

IsIdempotentAdd := function(add)
  local n, x;
  n := Length(add);

  for x in [1..n] do
    if add[x][x] <> x then
      return false;
    fi;
  od;

  return true;
end;

IsAbsorptiveAdd := function(add, one)
  local n, x;
  n := Length(add);

  for x in [1..n] do
    if add[one][x] <> one then
      return false;
    fi;
  od;

  return true;
end;

IsTimesDistributiveOverMonus := function(mul, sub)
  local n, x, y, z;
  n := Length(mul);

  for x in [1..n] do
    for y in [1..n] do
      for z in [1..n] do
        if mul[x][sub[y][z]] <> sub[mul[x][y]][mul[x][z]] then
          return false;
        fi;
      od;
    od;
  od;

  return true;
end;

IsMonusRightDistributiveOverPlus := function(add, sub)
  local n, x, y, z;
  n := Length(add);

  for x in [1..n] do
    for y in [1..n] do
      for z in [1..n] do
        if sub[add[x][y]][z] <> add[sub[x][z]][sub[y][z]] then
          return false;
        fi;
      od;
    od;
  od;

  return true;
end;

n := 3;
S := SemiringsOfSize(n);

Print("Found ", Length(S), " commutative m-semirings.\n");
for s in S do
  Print(s, "\n");
  Print("Idempotent? ", IsIdempotentAdd(s.add), "\n");
  Print("Absorptive? ", IsAbsorptiveAdd(s.add, s.one), "\n");
  Print("A13? ", IsTimesDistributiveOverMonus(s.mul, s.sub), "\n");
  Print("A14? ", IsMonusRightDistributiveOverPlus(s.add, s.sub), "\n");
  Print("\n");
od;
