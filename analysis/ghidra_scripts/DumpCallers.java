// DumpCallers.java - walks up the graph: lists callers of seed functions and decompiles them.
// Seeds = port_dfu parser (FUN_100cfe94) + helpers, to find the protocol_file_tran dispatcher.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.util.*;

public class DumpCallers extends GhidraScript {
    long[] seeds = { 0x100cfe94L, 0x10123844L, 0x100d0000L, 0x100d0018L };

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
        LinkedHashSet<Long> callers = new LinkedHashSet<>();

        println("===== CALLERS =====");
        for (long s : seeds) {
            Address a = toAddr(s);
            Function sf = getFunctionAt(a);
            String sn = sf != null ? sf.getName() : ("0x"+Long.toHexString(s));
            println("\n-- callers of " + sn + " @0x" + Long.toHexString(s) + " --");
            ReferenceIterator ri = rm.getReferencesTo(a);
            boolean any=false;
            while (ri.hasNext()) {
                any=true;
                Reference ref = ri.next();
                Address from = ref.getFromAddress();
                Function cf = getFunctionContaining(from);
                if (cf != null) {
                    println("   call @" + from + "  in " + cf.getName() + " @" + cf.getEntryPoint()
                            + "  [" + ref.getReferenceType() + "]");
                    callers.add(cf.getEntryPoint().getOffset());
                } else {
                    println("   ref @" + from + "  (NO FUNC) [" + ref.getReferenceType() + "]");
                }
            }
            if(!any) println("   (no direct callers)");
        }

        println("\n===== DECOMPILE CALLERS (" + callers.size() + ") =====");
        for (Long off : callers) {
            Function f = getFunctionAt(toAddr(off));
            if (f == null) { println("== NO FUNC @0x"+Long.toHexString(off)); continue; }
            println("\n==== " + f.getName() + " @ " + f.getEntryPoint() + " ====");
            println(decomp(f));
        }
        di.dispose();
    }
}
