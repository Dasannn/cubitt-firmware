// CallerTree.java - BFS hacia arriba por el grafo de llamadas desde semillas (escritor/apply sdfs)
// hasta hallar el dispatcher del canal de archivos BLE. Decompila todo lo encontrado.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.util.*;

public class CallerTree extends GhidraScript {
    long[] seeds = { 0x10104f3cL, 0x101046b4L };
    int MAXLEVEL = 3;
    DecompInterface di;

    private String decomp(Function f) {
        DecompileResults r = di.decompileFunction(f, 90, monitor);
        if (r != null && r.decompileCompleted()) return r.getDecompiledFunction().getC();
        return "(decompile failed)";
    }

    @Override
    public void run() throws Exception {
        di = new DecompInterface();
        di.openProgram(currentProgram);
        ReferenceManager rm = currentProgram.getReferenceManager();

        LinkedHashSet<Long> all = new LinkedHashSet<>();
        Set<Long> frontier = new LinkedHashSet<>();
        for (long s : seeds) frontier.add(s);

        for (int lvl = 0; lvl < MAXLEVEL && !frontier.isEmpty(); lvl++) {
            println("==== LEVEL " + lvl + " (" + frontier.size() + " funcs) ====");
            Set<Long> next = new LinkedHashSet<>();
            for (Long off : frontier) {
                all.add(off);
                Function f = getFunctionAt(toAddr(off));
                String fn = f != null ? f.getName() : ("0x"+Long.toHexString(off));
                ReferenceIterator ri = rm.getReferencesTo(toAddr(off));
                List<String> callers = new ArrayList<>();
                while (ri.hasNext()) {
                    Reference ref = ri.next();
                    if (!ref.getReferenceType().isCall() && !ref.getReferenceType().isFlow()) continue;
                    Function cf = getFunctionContaining(ref.getFromAddress());
                    if (cf != null) {
                        long co = cf.getEntryPoint().getOffset();
                        callers.add(cf.getName()+"@"+cf.getEntryPoint());
                        if (!all.contains(co)) next.add(co);
                    }
                }
                println("  " + fn + " <- [" + String.join(", ", callers) + "]");
            }
            frontier = next;
        }

        println("\n==== DECOMPILES (" + all.size() + ") ====");
        for (Long off : all) {
            Function f = getFunctionAt(toAddr(off));
            if (f == null) continue;
            println("\n---- " + f.getName() + " @ " + f.getEntryPoint() + " ----");
            println(decomp(f));
        }
        di.dispose();
    }
}
