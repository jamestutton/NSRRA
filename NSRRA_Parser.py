import logging
import sys

import pandas as pd
from pydantic import BaseModel
from typing import Union

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.info("Starting")

root = logging.getLogger()
root.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.WARNING)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
root.addHandler(handler)

def is_letter_after_L(letter):
    return ord(letter.upper()) >= ord('L')

SecondClaims = {
    "Amanda Kelly": "Stoke FIT",
    "Michelle Dalgarno": "Stoke FIT",
    "Andrew Kane": "Stoke FIT",
}

class NSRRA(BaseModel):
    class Member(BaseModel):
        name: str
        sex: str =""
        points: int = 0
        races: int = 0
        avg: float = 0
        group: str = ""
        age_group: str = ""
        club: str = ""
        
        @property
        def second_claim(self):
            if self.name in SecondClaims:
                return  SecondClaims[self.name]

        def index(self):
            return f"{self.name}"

    class Club(BaseModel):
        class ClubStats(BaseModel):
            name: str
            sex: str = "M"
            races: int = 0
            points: int = 0 
            members: Union[None,list["NSRRA.Member"]] = None
            size: int = 6

            @property
            def include(self) -> bool:
                if self.races > 0 and self.races >= (self.size * 1.5):
                    return True
                return False
                

            @property
            def Avg(self) -> int:
                if self.points > 0 and self.races > 0:
                    return self.points / self.races
                else:
                    return 0

            def GenerateStats(self):
                self.points = 0
                self.races = 0 
                for member in self.members:
                    logger.debug(f"TEAM:{self.name} Adding {member.points} for {member.name} from {member.races}races")
                    self.points += member.points
                    self.races += member.races

            @property
            def Summary(self):
                return {'Name': self.name, 'Races': self.races, "Points": self.points, 'Avg': self.Avg}
            
            @property  
            def Summary_df(self) -> pd.DataFrame:
                return pd.DataFrame({'Name': [self.name], 'Races': [self.races], "Points": [self.points], 'Avg': [self.Avg]}) 
        
        name: str
        members: dict[str,"NSRRA.Member"] = {}

        MaleTeam: Union[None,"NSRRA.Club.ClubStats"] = None
        FemaleTeam: Union[None,"NSRRA.Club.ClubStats"] = None
        
        

        def GenerateStats(self):
            #Male Team
            self.MaleTeam = self.ClubStats(name=self.name,sex="M")
            self.MaleTeam.members = self.TopXMembers(self.MaleTeam.size,self.MaleTeam.sex)
            self.MaleTeam.GenerateStats()

            #Female Team
            self.FemaleTeam = self.ClubStats(name=self.name,sex="F",size=4)
            self.FemaleTeam.members = self.TopXMembers(self.FemaleTeam.size,self.FemaleTeam.sex)
            self.FemaleTeam.GenerateStats()

            
                

        def TopXMembers(self,size=6,sex="M") -> list["NSRRA.Member"]:
            top_scorers = {}
            members_list = self.members.values()
            filt_members = [member for member in members_list if member.sex == sex]
            top_scorers = sorted(filt_members, key=lambda member: member.points, reverse=True)[:size]
            return top_scorers

        def AddMember(self,team_member:"NSRRA.Member"):
            self.members[team_member.index] = team_member

    class Clubs(BaseModel):
        clubs: dict[str,"NSRRA.Club"] = {}
        

        def GenerateStats(self):
            clubs = self.clubs.values()
            for club in clubs:
                club.GenerateStats() 
        
        @property
        def MaleTeams_df(self):
            teams_list = list(self.clubs.values())  # get a list of all clubs
            teams_list_sorted = sorted(teams_list, key=lambda club: club.MaleTeam.points, reverse=True)
            logger.debug(teams_list_sorted)
            df = pd.DataFrame(columns=['Name','Points','Races','Avg'])
            df.set_index("Name")
            for club in teams_list_sorted:
                if club.MaleTeam.include:
                    df = pd.concat([df,club.MaleTeam.Summary_df], ignore_index=True)
            return df

        @property
        def FemaleTeams_df(self):
            teams_list = list(self.clubs.values())  # get a list of all clubs
            teams_list_sorted = sorted(teams_list, key=lambda club: club.FemaleTeam.points, reverse=True)
            logger.debug(teams_list_sorted)
            df = pd.DataFrame(columns=['Name','Points','Races','Avg'])
            df.set_index("Name")
            for club in teams_list_sorted:
                if club.FemaleTeam.include:
                    df = pd.concat([df,club.FemaleTeam.Summary_df], ignore_index=True)
            return df

            

        def AutoTeamTable(self):
            self.GenerateStats()
            print("\n======Male Teams======")
            print("#### By Points")
            print(self.MaleTeams_df)
            print("#### By Avg")
            print(self.MaleTeams_df.sort_values('Avg', ascending=False))

            print("\n======Female Teams======")
            print("#### By Points")
            print(self.FemaleTeams_df)
            print("#### By Avg")
            print(self.FemaleTeams_df.sort_values('Avg', ascending=False))    
            

        def AddTeam(self,club:"NSRRA.Club"):
            self.clubs[club.name] = club

    class BaseGroup(BaseModel):
        name: str
        members: dict[int,"NSRRA.Member"] = {}
        suffix: str = "Group "
        group_type: str = "Generic"

        def __str__(self):
            return f"{self.suffix}{self.name}"

        def AddPositionedMember(self,pos:int,member:"NSRRA.Member"):
            self.members[pos] = member


        def Summary(self):
        
            msg = f"{self.suffix}{self.name}: "
            for pos, o_member in self.members.items():
                msg +=(f"{o_member.name} {self.add_th(pos)}({o_member.avg}/{o_member.points}), ")
            out = f"{msg[:-2]} out of {len(self.members)}"
            print(out)

        def ClubSummary(self,club:str="Stoke FIT") -> tuple[int,str]:
            hits=0  
            msg = f"{self.suffix}{self.name}: "
            for pos, o_member in self.members.items():
                if o_member.club == club:
                    msg +=(f"{o_member.name} {self.add_th(pos)}({o_member.avg}/{o_member.points}), ")
                    hits+=1
                elif o_member.second_claim == club:
                    msg +=(f"{o_member.name} {self.add_th(pos)}({o_member.avg}/{o_member.points}), ")
                    hits+=1
            out = f"{msg[:-2]} out of {len(self.members)}"
            return(hits,out)     

        def ClubSummaryTable(self,club:str="Stoke FIT") -> tuple[int,str]:
            hits=0  
            msg = f"{self.suffix}{self.name} (out of {len(self.members)}):"
            for pos, o_member in self.members.items():
                if o_member.club == club or o_member.second_claim == club:
                    msg +=(f"\n  {self.add_th(pos)} {o_member.name} {o_member.points} Pts,{o_member.avg} Avg,{o_member.races} Rs")
                    hits+=1
            return(hits,msg)                

        def add_th(self,num):
            if 11 <= num <= 13:
                return str(num) + "th"
            else:
                last_digit = num % 10
                if last_digit == 1:
                    return str(num) + "st"
                elif last_digit == 2:
                    return str(num) + "nd"
                elif last_digit == 3:
                    return str(num) + "rd"
                else:
                    return str(num) + "th"               
            
    class LetterGroup(BaseGroup):
        suffix: str = "Group "
        group_type: str ="Letter"

    class AgeGroup(BaseGroup):
        suffix: str = ""
        group_type: str ="Age"

        
    class Groups(BaseModel):
        groups: dict[str,"NSRRA.BaseGroup"] = {}

        def Add(self,group:"NSRRA.BaseGroup"):
            self.groups[group.name] = group

        def Summary(self):
            groups = self.groups.values()
            for group in groups:
                group.Summary()

        def ClubSummary(self,club:str="Stoke FIT"):  
            groups = self.groups.values()
            for group in groups:
                hits,msg = group.ClubSummary(club)            
                if hits >= 1:
                    print(msg)

        def ClubSummaryTable(self,club:str="Stoke FIT"):  
            groups = self.groups.values()
            for group in groups:
                hits,msg = group.ClubSummaryTable(club)            
                if hits >= 1:
                    print(msg)



    clubs = Clubs()
    groups = Groups()
    age_groups = Groups()
    ranks = Groups()
    members: dict[str,"NSRRA.Member"] = {}

    def AddMember(self,member:"NSRRA.Member"):
        self.members[member.index] = member
        

    def ClubSummary(self,club:str="Stoke FIT"):  
        print(f"#############################################")
        print(f"Latest NSRRA Member Stats for {club}")
        print(f"#############################################")
        print("------------------")
        print("NSRRA Groups:")
        print("------------------")
        self.groups.ClubSummary(club)
        print("------------------")
        print("Age Groups:")
        print("------------------")
        self.age_groups.ClubSummary(club)

    def ClubSummaryTable(self,club:str="Stoke FIT"):  
        print(f"#############################################")
        print(f"Latest NSRRA Member Stats for {club}")
        print(f"#############################################")
        print("------------------")
        print("NSRRA Groups:")
        print("------------------")
        self.groups.ClubSummaryTable(club)
        print("------------------")
        print("Age Groups:")
        print("------------------")
        self.age_groups.ClubSummaryTable(club)        
    
    def ClubTables(self):
        self.clubs.AutoTeamTable()

    def GroupLetterPointsCalculator(self,group_df):
        t_Group = group_df.columns[2]
        GroupLetter = str(t_Group).split()[1]
        

        if GroupLetter not in self.groups.groups:   
            o_group = self.LetterGroup(name=GroupLetter)
            self.groups.Add(o_group)     
        sex = "M"
        if is_letter_after_L(GroupLetter):
            sex = "F"
        
        logger.info(f"{o_group} processing.... ")    
        for index, row in group_df.iterrows():
                
                try:
                    name = row[2]
                    points = row[0]
                    races = row[1]
                    avg = row[5]
                    try: 
                        if pd.isna(row[4]):
                            club = "UNKNOWN"
                        else:
                            club = row[4]
                    except Exception as ex:
                        club = "UNKNOWN_EX"
                    if club not in self.clubs.clubs:
                        self.clubs.AddTeam(self.Club(name=club))
                    o_team=self.clubs.clubs[club]

                    member = self.Member(name=name,points=points,avg=avg,sex=sex,races=races,club=o_team.name,group=o_group.name)
                    if member.index not in self.members:
                        self.AddMember(member)
                    member = self.members[member.index]
                    
                    
                    logger.debug(f"NAME {name} processing.... ")
                    o_team.AddMember(member)
                    o_group.AddPositionedMember(index+1,member)
                except Exception as ex:
                    logger.warning(f"Cant add {name} to {o_group}")
                    logger.debug(f"{ex}",stack_info=True)
        logger.info(f"{o_group} done. ")

    def AgeGroupPointsCalculator(self,group_df):
        age_Group = group_df.columns[2]
        
         

        if age_Group not in self.age_groups.groups:   
            o_group = self.AgeGroup(name=age_Group)
            self.age_groups.Add(o_group)     
        logger.info(f"{o_group} processing.... ")    
        for index, row in group_df.iterrows():
                

            
            
                try:
                    name = row[2]
                    points = row[0]
                    races = row[1]
                    avg = row[5]
                    try: 
                        if pd.isna(row[4]):
                            club = "UNKNOWN"
                        else:
                            club = row[4]
                    except Exception as ex:
                        club = "UNKNOWN_EX"
                    if club not in nsrra.clubs.clubs:
                        nsrra.clubs.AddTeam(self.Club(name=club))
                    o_team=self.clubs.clubs[club]

                    
                    member = self.Member(name=name,points=points,avg=avg,races=races,club=o_team.name,group=o_group.name)
                    if member.index not in self.members:
                        self.AddMember(member)
                    member = self.members[member.index]
                    member.age_group = age_Group
                    
                    logger.debug(f"NAME {name} processing.... ")
                    o_team.AddMember(member)
                    o_group.AddPositionedMember(index+1,member)
                except Exception as ex:
                    logger.warning(f"Cant add {name} to {o_group}")
                    logger.warning(f"{ex}",stack_info=True)
        logger.info(f"{o_group} done. ")

  
    





    


nsrra = NSRRA()

    
    


# Load the Excel file into a pandas dataframe
df = pd.read_excel('NSRRA-latest.xls', header=None)

# Find the indices of rows starting with "Pts"
pts_indices = df[df[4] == 'Club'].index.tolist()

# Append the last row index to the list of indices
pts_indices.append(len(df))

# Split the data frame into a list of data frames based on the indices
dfs = [df.iloc[pts_indices[i]:pts_indices[i+1]] for i in range(len(pts_indices)-1)]

for temp_df in dfs:
    group_df = pd.DataFrame(temp_df.values[1:], columns=temp_df.iloc[0])
    Group = group_df.columns[2]
    if str(Group).startswith("Group"):
        nsrra.GroupLetterPointsCalculator(group_df)
    elif str(Group).startswith("Male Ranks"):
        pass 
    elif str(Group).startswith("Lady Ranks"):
        pass 
    elif str(Group).startswith("Male"):
        nsrra.AgeGroupPointsCalculator(group_df)
    elif str(Group).startswith("Lady"):
        nsrra.AgeGroupPointsCalculator(group_df)        
    try:
        #BuildClubSummary(group_df)
        pass
        #BuildClubSummary(group_df,"Biddulph RC")
    except ValueError as e:
        logger.error(e,stack_info=True)
        pass 
#print(nsrra)
#nsrra.ClubSummary("Trentham RC")
#nsrra.ClubSummary("UNKNOWN")

nsrra.ClubSummary()
nsrra.ClubSummaryTable()
# Club Points Tables
# nsrra.ClubTables()
        
