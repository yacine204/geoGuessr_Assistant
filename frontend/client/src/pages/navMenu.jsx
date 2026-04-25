import { useState } from "react"

function NavMenu({cord}){
    if (cord) console.log(cord)


    return(
        <div>
            <div>
                <button>Pause Rotation</button>
                <button>Next Candidate Coord</button>
                <div>Top Countries</div>
                {/* todo: countries are arranged from top confidence to lowest */}
                <div>
                    <ul>
                    {cord?.top_countries.map((country)=> (
                        <li key={country}>{country}</li>
                    ))}
                    </ul>
                </div>
            </div>
        </div>
    )
}

export default NavMenu