
from checks.base_check import BaseCheck

class DateGapCheck(BaseCheck):

    def inner_run(self, db):
        cur = db.cursor()

        query = """
            select count(*) from (select abs(datediff(lead(cast(`%(col)s` as timestamp), 1) over (order by cast(`%(col)s` as timestamp)), cast(`%(col)s` as timestamp))) as diff, `%(col)s` from `%(schema)s`.`%(table)s`) t where diff > 1
        """ % self.query_settings

        self.add_log("collection", "Run query %s" % (query))
        
        cur.execute(query)

        row = cur.fetchone()

        self.add_log("result", "Query came back with count %s" %(row[0]))

        self.failed = row[0] > 0

        self.failed_rows_query = """
                select gap_start, gap_end from (
                    select `%(col)s` as gap_start, cast(`%(col)s` as timestamp) + interval diff days as gap_end from 
                        (
                            select abs(datediff(lead(cast(`%(col)s` as timestamp), 1) over (order by cast(`%(col)s` as timestamp)), cast(`%(col)s` as timestamp))) as diff, `%(col)s` from `%(schema)s`.`%(table)s`) t where diff > 1 limit 10000
                        ) t2
                    where gap_end is not null
            """ % self.query_settings
