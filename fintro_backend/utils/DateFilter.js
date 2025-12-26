export const getDateFilter = (from, to, field) => {
  if (!from && !to) return undefined;

  const filter = {};
  if (from) filter.gte = new Date(from);
  if (to) filter.lte = new Date(to);

  return { [field]: filter };
};
